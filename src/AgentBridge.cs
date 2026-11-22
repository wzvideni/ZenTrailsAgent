// ZenTrails Agent Bridge — BepInEx 5 plugin, C# 5 syntax (framework csc)
// Exposes a line-protocol TCP control surface on 127.0.0.1:5123, executed on Unity's main thread.
using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using BepInEx;
using BepInEx.Logging;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace ZenTrailsAgent
{
    public class Result
    {
        public bool Ok = true;
        public string Payload = "";
        public static Result Good(string s) { return new Result { Ok = true, Payload = s ?? "" }; }
        public static Result Bad(string s) { return new Result { Ok = false, Payload = s ?? "" }; }
    }

    public class Job
    {
        public Client Src;
        public string Seq;
        public string Cmd;
        public string[] Args;
    }

    public class Client
    {
        readonly TcpClient _tcp;
        readonly NetworkStream _ns;
        readonly ConcurrentQueue<byte[]> _outbox = new ConcurrentQueue<byte[]>();
        readonly ConcurrentQueue<Job> _jobs;
        readonly ManualLogSource _log;
        volatile bool _closed;

        public Client(TcpClient tcp, ConcurrentQueue<Job> jobs, ManualLogSource log)
        {
            _tcp = tcp; _ns = tcp.GetStream(); _jobs = jobs; _log = log;
        }

        public void Start()
        {
            var tr = new Thread(ReadLoop) { IsBackground = true };
            var tw = new Thread(WriteLoop) { IsBackground = true };
            tr.Start(); tw.Start();
        }

        void ReadLoop()
        {
            var buf = new MemoryStream();
            var chunk = new byte[8192];
            try
            {
                while (!_closed)
                {
                    int n = _ns.Read(chunk, 0, chunk.Length);
                    if (n <= 0) break;
                    buf.Write(chunk, 0, n);
                    byte[] data = buf.ToArray();
                    int start = 0;
                    for (int i = 0; i < data.Length; i++)
                    {
                        if (data[i] != (byte)'\n') continue;
                        string line = Encoding.UTF8.GetString(data, start, i - start).TrimEnd('\r');
                        start = i + 1;
                        if (line.Length == 0) continue;
                        Enqueue(line);
                    }
                    buf.SetLength(0);
                    if (start < data.Length) buf.Write(data, start, data.Length - start);
                }
            }
            catch (Exception) { }
            finally { Close(); }
        }

        void Enqueue(string line)
        {
            var parts = line.Split('\t');
            if (parts.Length < 2) return;
            var job = new Job { Src = this, Seq = parts[0], Cmd = parts[1], Args = parts.Skip(2).ToArray() };
            _jobs.Enqueue(job);
        }

        void WriteLoop()
        {
            try
            {
                while (!_closed)
                {
                    byte[] msg;
                    if (!_outbox.TryDequeue(out msg)) { Thread.Sleep(5); continue; }
                    _ns.Write(msg, 0, msg.Length);
                    _ns.Flush();
                }
            }
            catch (Exception) { Close(); }
        }

        public void Send(string seq, bool ok, string payload)
        {
            if (payload == null) payload = "";
            if (payload.Length > 400000) payload = payload.Substring(0, 400000) + "\n...[truncated]";
            byte[] body = Encoding.UTF8.GetBytes(payload);
            string head = "R\t" + seq + "\t" + (ok ? "OK" : "ERR") + "\t" + body.Length + "\n";
            byte[] hb = Encoding.UTF8.GetBytes(head);
            var all = new byte[hb.Length + body.Length];
            Buffer.BlockCopy(hb, 0, all, 0, hb.Length);
            Buffer.BlockCopy(body, 0, all, hb.Length, body.Length);
            _outbox.Enqueue(all);
        }

        public void Close()
        {
            if (_closed) return;
            _closed = true;
            try { _tcp.Close(); } catch (Exception) { }
        }
    }

    [BepInPlugin("com.dc.zentrails.agent", "ZenTrails Agent Bridge", "1.0.0")]
    public class AgentPlugin : BaseUnityPlugin
    {
        public const int Port = 5123;
        static AgentPlugin _inst;
        TcpListener _listener;
        readonly ConcurrentQueue<Job> _jobs = new ConcurrentQueue<Job>();
        readonly List<Client> _clients = new List<Client>();
        int _frames;

        void Awake()
        {
            _inst = this;
            try
            {
                _listener = new TcpListener(IPAddress.Loopback, Port);
                _listener.Start();
                var t = new Thread(AcceptLoop) { IsBackground = true, Name = "ZT-Accept" };
                t.Start();
                Logger.LogMessage("[AgentBridge] listening on 127.0.0.1:" + Port);
            }
            catch (Exception e)
            {
                Logger.LogError("[AgentBridge] listen failed: " + e.Message);
            }
        }

        void AcceptLoop()
        {
            while (true)
            {
                TcpClient tcp;
                try { tcp = _listener.AcceptTcpClient(); }
                catch (Exception) { return; }
                tcp.NoDelay = true;
                var c = new Client(tcp, _jobs, Logger);
                lock (_clients) { _clients.Add(c); }
                c.Start();
                Logger.LogMessage("[AgentBridge] client connected");
            }
        }

        readonly Queue<Action> _inputQueue = new Queue<Action>();

        public void EnqueueAction(Action a)
        {
            lock (_inputQueue) { _inputQueue.Enqueue(a); }
        }

        void Update()
        {
            _frames++;
            // one injected input step per frame, so the game's own Update sees each event
            for (int i = 0; i < 2; i++)
            {
                Action act = null;
                lock (_inputQueue) { if (_inputQueue.Count > 0) act = _inputQueue.Dequeue(); }
                if (act == null) break;
                try { act(); } catch (Exception e) { Logger.LogError("[AgentBridge] input: " + e.Message); }
            }
            Job job;
            int handled = 0;
            while (handled < 16 && _jobs.TryDequeue(out job))
            {
                Result r;
                try { r = CommandRouter.Execute(job, this); }
                catch (Exception e)
                {
                    r = Result.Bad("EXCEPTION " + e.GetType().Name + ": " + e.Message + "\n" + e.StackTrace);
                }
                if (job.Cmd != "wait")
                {
                    if (job.Cmd != "ping") Logger.LogInfo("[cmd] " + job.Cmd + " " + string.Join(" ", job.Args) + " -> " + (r.Ok ? "OK" : "ERR"));
                    job.Src.Send(job.Seq, r.Ok, r.Payload);
                }
                handled++;
            }
        }

        void OnDestroy()
        {
            try { if (_listener != null) _listener.Stop(); } catch (Exception) { }
        }
    }

    public static class CommandRouter
    {
        public static int FrameCount { get; set; }

        public static Result Execute(Job job, AgentPlugin plugin)
        {
            switch (job.Cmd)
            {
                case "ping": return Result.Good("pong zen=" + Time.frameCount + " fps=" + Math.Round(1.0 / Math.Max(0.0001, Time.smoothDeltaTime)) );
                case "types": return Types(job.Args);
                case "describe": return Describe(job.Args);
                case "scene": return Scene(job.Args);
                case "find": return Find(job.Args);
                case "get": return Get(job.Args);
                case "set": return Set(job.Args);
                case "call": return Call(job.Args);
                case "coroutine": return Coroutine(job.Args);
                case "shot": return Shot(job.Args);
                case "mouse": return Mouse(job.Args);
                case "key": return Key(job.Args);
                case "focus": return Focus(job.Args);
                case "move": return MoveCmd(job.Args, plugin);
                case "down": return BtnCmd("down", job.Args, plugin);
                case "up": return BtnCmd("up", job.Args, plugin);
                case "click": return ClickCmd(job.Args, plugin);
                case "drag": return DragCmd(job.Args, plugin);
                case "log": return Log(job.Args);
                case "input": return InputProbe(job.Args);
                case "clickui": return ClickUi(job.Args);
                case "bytes": return Bytes(job.Args);
                default: return Result.Bad("unknown command: " + job.Cmd);
            }
        }

        // ---------- introspection ----------

        static IEnumerable<Type> AllTypes()
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                string an = asm.GetName().Name;
                if (an.StartsWith("System") || an.StartsWith("Microsoft") || an.StartsWith("mscorlib")) continue;
                Type[] ts;
                try { ts = asm.GetTypes(); }
                catch (ReflectionTypeLoadException e) { ts = e.Types.Where(t => t != null).ToArray(); }
                catch (Exception) { continue; }
                foreach (var t in ts) yield return t;
            }
        }

        static Type ResolveType(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            var exact = AllTypes().FirstOrDefault(t => t.FullName == name || t.Name == name);
            if (exact != null) return exact;
            return AllTypes().FirstOrDefault(t => (t.FullName ?? t.Name).IndexOf(name, StringComparison.OrdinalIgnoreCase) >= 0);
        }

        static Result Types(string[] args)
        {
            string filter = args.Length > 0 ? args[0] : "";
            var sb = new StringBuilder();
            int count = 0;
            foreach (var t in AllTypes().OrderBy(t => t.FullName))
            {
                if (filter.Length > 0 && (t.FullName == null || t.FullName.IndexOf(filter, StringComparison.OrdinalIgnoreCase) < 0)) continue;
                sb.Append(t.FullName).Append(t.IsEnum ? "  [enum]" : "").Append('\n');
                count++;
                if (count >= 500) { sb.Append("... more\n"); break; }
            }
            return Result.Good("types=" + count + "\n" + sb);
        }

        static Result Describe(string[] args)
        {
            var t = ResolveType(args.Length > 0 ? args[0] : "");
            if (t == null) return Result.Bad("type not found");
            var sb = new StringBuilder();
            sb.Append("type ").Append(t.FullName).Append('\n');
            sb.Append("base ").Append(t.BaseType != null ? t.BaseType.FullName : "-").Append('\n');
            sb.Append("assembly ").Append(t.Assembly.GetName().Name).Append('\n');
            if (t.IsEnum)
            {
                foreach (var v in Enum.GetValues(t)) sb.Append("  enum ").Append(v).Append(" = ").Append((int)Convert.ToInt64(v)).Append('\n');
                return Result.Good(sb.ToString());
            }
            const BindingFlags F = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly;
            foreach (var f in t.GetFields(F))
                sb.Append("  field ").Append(f.IsStatic ? "static " : "").Append(TypeName(f.FieldType)).Append(' ').Append(f.Name).Append('\n');
            foreach (var p in t.GetProperties(F))
                sb.Append("  prop ").Append(TypeName(p.PropertyType)).Append(' ').Append(p.Name)
                  .Append(p.CanRead ? " get" : "").Append(p.CanWrite ? " set" : "").Append('\n');
            foreach (var m in t.GetMethods(F).Where(m => !m.IsSpecialName))
                sb.Append("  method ").Append(m.IsStatic ? "static " : "").Append(TypeName(m.ReturnType)).Append(' ')
                  .Append(m.Name).Append('(')
                  .Append(string.Join(", ", m.GetParameters().Select(p => TypeName(p.ParameterType) + " " + p.Name).ToArray()))
                  .Append(")\n");
            return Result.Good(sb.ToString());
        }

        static string TypeName(Type t)
        {
            if (t == null) return "?";
            if (!t.IsGenericType) return t.Name;
            return t.Name.Split('`')[0] + "<" + string.Join(",", t.GetGenericArguments().Select(TypeName).ToArray()) + ">";
        }

        static string GoPath(Transform tr)
        {
            var parts = new List<string>();
            while (tr != null) { parts.Insert(0, tr.name); tr = tr.parent; }
            return "/" + string.Join("/", parts.ToArray());
        }

        static IEnumerable<UnityEngine.Object> AllObjects(Type t)
        {
            var arr = Resources.FindObjectsOfTypeAll(t);
            foreach (var o in arr)
            {
                var comp = o as Component;
                if (comp != null)
                {
                    if (!comp.gameObject.scene.IsValid()) continue;
                    if ((comp.hideFlags & HideFlags.NotEditable) != 0) continue;
                    yield return o;
                    continue;
                }
                var go = o as GameObject;
                if (go != null)
                {
                    if (!go.scene.IsValid()) continue;
                    yield return o;
                    continue;
                }
                yield return o;
            }
        }

        static Result Scene(string[] args)
        {
            int depth = args.Length > 0 ? int.Parse(args[0]) : 2;
            var sb = new StringBuilder();
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var sc = SceneManager.GetSceneAt(i);
                sb.Append("scene ").Append(sc.name).Append(" loaded=").Append(sc.isLoaded).Append(" roots=").Append(sc.rootCount).Append('\n');
                foreach (var go in sc.GetRootGameObjects())
                    DumpGo(go.transform, sb, 0, depth);
            }
            return Result.Good(sb.ToString());
        }

        static void DumpGo(Transform tr, StringBuilder sb, int lvl, int maxDepth)
        {
            string pad = new string(' ', lvl * 2);
            var comps = tr.GetComponents<Component>().Where(c => c != null).Select(c => c.GetType().Name).ToArray();
            sb.Append(pad).Append(tr.name).Append("  [").Append(string.Join(",", comps)).Append("]")
              .Append(tr.gameObject.activeSelf ? "" : " (inactive)").Append('\n');
            if (lvl >= maxDepth) return;
            for (int i = 0; i < tr.childCount; i++) DumpGo(tr.GetChild(i), sb, lvl + 1, maxDepth);
        }

        static Result Find(string[] args)
        {
            var t = ResolveType(args.Length > 0 ? args[0] : "");
            if (t == null) return Result.Bad("type not found");
            var sb = new StringBuilder();
            int n = 0;
            foreach (var o in AllObjects(t))
            {
                string path = "";
                var comp = o as Component;
                if (comp != null) path = GoPath(comp.transform);
                else { var go = o as GameObject; if (go != null) path = GoPath(go.transform); }
                sb.Append("obj ").Append(o.GetInstanceID()).Append(' ').Append(o.name).Append("  ").Append(path).Append('\n');
                n++;
                if (n >= 200) { sb.Append("...\n"); break; }
            }
            return Result.Good("found=" + n + " type=" + t.FullName + "\n" + sb);
        }

        // ---------- object resolution + member access ----------

        static object Resolve(string selector)
        {
            if (string.IsNullOrEmpty(selector)) return null;
            if (selector.StartsWith("obj:"))
            {
                int id;
                if (!int.TryParse(selector.Substring(4), out id)) return null;
                foreach (var o in Resources.FindObjectsOfTypeAll(typeof(UnityEngine.Object)))
                    if (o.GetInstanceID() == id) return o;
                return null;
            }
            if (selector.StartsWith("path:"))
            {
                var go = GameObject.Find(selector.Substring(5));
                return go;
            }
            string tn = selector.StartsWith("type:") ? selector.Substring(5) : selector;
            var t = ResolveType(tn);
            if (t == null) return null;
            // static singleton convention
            foreach (var n in new[] { "instance", "Instance", "I", "_instance", "singleton", "Singleton", "Current", "current" })
            {
                var f = t.GetField(n, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
                if (f != null) { var v = f.GetValue(null); if (v != null) return v; }
                var p = t.GetProperty(n, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
                if (p != null && p.CanRead) { var v = p.GetValue(null, null); if (v != null) return v; }
            }
            return AllObjects(t).FirstOrDefault();
        }

        static MemberInfo FindMember(Type t, string name)
        {
            for (Type cur = t; cur != null; cur = cur.BaseType)
            {
                var f = cur.GetField(name, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
                if (f != null) return f;
                var p = cur.GetProperty(name, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
                if (p != null) return p;
            }
            return null;
        }

        static object GetMember(object obj, string name)
        {
            if (obj == null) return null;
            var mi = FindMember(obj.GetType(), name);
            if (mi == null) throw new Exception("member '" + name + "' not found on " + obj.GetType().Name);
            var f = mi as FieldInfo;
            if (f != null) return f.GetValue(f.IsStatic ? null : obj);
            var p = mi as PropertyInfo;
            return p.GetValue(p.GetStatic() ? null : obj, null);
        }

        static bool GetStatic(this PropertyInfo p)
        {
            var g = p.GetGetMethod(true);
            return g != null && g.IsStatic;
        }

        static string Fmt(object v)
        {
            if (v == null) return "null";
            var uo = v as UnityEngine.Object;
            if (uo != null) return uo.name + "(id=" + uo.GetInstanceID() + ")";
            if (v is string) return (string)v;
            if (v is IEnumerable && !(v is string))
            {
                var parts = new List<string>();
                int i = 0;
                foreach (var e in (IEnumerable)v) { parts.Add(Fmt(e)); if (++i >= 40) { parts.Add("..."); break; } }
                return "[" + string.Join(", ", parts.ToArray()) + "]";
            }
            var t = v.GetType();
            if (t.IsPrimitive || t.IsEnum || v is decimal) return v.ToString();
            var sb = new StringBuilder();
            sb.Append(t.Name).Append("{");
            foreach (var f in t.GetFields(BindingFlags.Public | BindingFlags.Instance).Take(20))
                sb.Append(f.Name).Append("=").Append(Fmt(f.GetValue(v))).Append(" ");
            foreach (var p in t.GetProperties(BindingFlags.Public | BindingFlags.Instance).Take(20))
            {
                if (!p.CanRead || p.GetIndexParameters().Length > 0) continue;
                try { sb.Append(p.Name).Append("=").Append(Fmt(p.GetValue(v, null))).Append(" "); }
                catch (Exception) { }
            }
            sb.Append("}");
            return sb.ToString();
        }

        static Result Get(string[] args)
        {
            // get <selector> [member.member...]
            if (args.Length < 1) return Result.Bad("usage: get <selector> [members]");
            object obj = Resolve(args[0]);
            if (obj == null) return Result.Bad("object not resolved: " + args[0]);
            if (args.Length == 1) return Result.Good(Fmt(obj));
            string[] path = args[1].Split('.');
            object cur = obj;
            var trace = new StringBuilder();
            foreach (var seg in path)
            {
                try { cur = GetMember(cur, seg); }
                catch (Exception e) { trace.Append(seg).Append(" ! ").Append(e.Message).Append('\n'); break; }
                trace.Append(seg).Append(" = ").Append(Fmt(cur)).Append('\n');
                if (cur == null) break;
            }
            return Result.Good(trace.ToString());
        }

        static object ConvertArg(string s, Type t)
        {
            if (s == "null" && !t.IsValueType) return null;
            if (t == typeof(string)) return s;
            var nt = Nullable.GetUnderlyingType(t);
            if (nt != null)
            {
                if (s == "null" || s.Length == 0) return null;
                return ConvertArg(s, nt);
            }
            if (t == typeof(Quaternion))
            {
                var q = s.Split(',').Select(x => float.Parse(x, System.Globalization.CultureInfo.InvariantCulture)).ToArray();
                if (q.Length == 1) return Quaternion.Euler(0f, 0f, q[0]);
                if (q.Length == 3) return Quaternion.Euler(q[0], q[1], q[2]);
                return new Quaternion(q[0], q[1], q[2], q[3]);
            }
            if (typeof(UnityEngine.Object).IsAssignableFrom(t) && (s.StartsWith("type:") || s.StartsWith("obj:") || s.StartsWith("path:")))
                return Resolve(s);
            if (t == typeof(int)) return int.Parse(s);
            if (t == typeof(float)) return float.Parse(s, System.Globalization.CultureInfo.InvariantCulture);
            if (t == typeof(double)) return double.Parse(s, System.Globalization.CultureInfo.InvariantCulture);
            if (t == typeof(long)) return long.Parse(s);
            if (t == typeof(bool)) return s == "1" || s.Equals("true", StringComparison.OrdinalIgnoreCase);
            if (t.IsEnum) return Enum.Parse(t, s, true);
            if (t == typeof(Vector2) || t == typeof(Vector3) || t == typeof(Vector4))
            {
                var nums = s.Split(',').Select(x => float.Parse(x, System.Globalization.CultureInfo.InvariantCulture)).ToArray();
                if (t == typeof(Vector2)) return new Vector2(nums[0], nums[1]);
                if (t == typeof(Vector3)) return new Vector3(nums[0], nums[1], nums.Length > 2 ? nums[2] : 0f);
                return new Vector4(nums[0], nums[1], nums.Length > 2 ? nums[2] : 0f, nums.Length > 3 ? nums[3] : 0f);
            }
            if (t == typeof(Color)) { var nums = s.Split(',').Select(x => float.Parse(x, System.Globalization.CultureInfo.InvariantCulture)).ToArray(); return new Color(nums[0], nums[1], nums[2], nums.Length > 3 ? nums[3] : 1f); }
            var conv = Convert.ChangeType(s, t);
            return conv;
        }

        static Result Set(string[] args)
        {
            if (args.Length < 3) return Result.Bad("usage: set <selector> <member.path> <value>");
            object obj = Resolve(args[0]);
            if (obj == null) return Result.Bad("object not resolved: " + args[0]);
            string[] path = args[1].Split('.');
            object holder = obj;
            for (int i = 0; i < path.Length - 1; i++) holder = GetMember(holder, path[i]);
            if (holder == null) return Result.Bad("holder null on path " + args[1]);
            string leaf = path[path.Length - 1];
            var mi = FindMember(holder.GetType(), leaf);
            if (mi == null) return Result.Bad("member not found: " + leaf);
            string old = Fmt(mi is FieldInfo ? ((FieldInfo)mi).GetValue(((FieldInfo)mi).IsStatic ? null : holder)
                                            : ((PropertyInfo)mi).GetValue(holder, null));
            Type vt = mi is FieldInfo ? ((FieldInfo)mi).FieldType : ((PropertyInfo)mi).PropertyType;
            object nv = ConvertArg(args[2], vt);
            if (mi is FieldInfo) ((FieldInfo)mi).SetValue(((FieldInfo)mi).IsStatic ? null : holder, nv);
            else ((PropertyInfo)mi).SetValue(holder, nv, null);
            return Result.Good("set " + args[1] + ": " + old + " -> " + Fmt(nv));
        }

        static Result Call(string[] args)
        {
            if (args.Length < 2) return Result.Bad("usage: call <selector> <method> [args...]");
            object obj = Resolve(args[0]);
            if (obj == null) return Result.Bad("object not resolved: " + args[0]);
            var t = obj.GetType();
            string name = args[1];
            string[] raw = args.Skip(2).ToArray();
            MethodInfo best = null;
            for (Type cur = t; cur != null && best == null; cur = cur.BaseType)
            {
                foreach (var m in cur.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly))
                {
                    if (m.Name != name) continue;
                    if (m.GetParameters().Length != raw.Length) continue;
                    best = m; break;
                }
            }
            if (best == null) return Result.Bad("method not found: " + name + "/" + raw.Length + " on " + t.Name);
            var ps = best.GetParameters();
            var conv = new object[ps.Length];
            for (int i = 0; i < ps.Length; i++) conv[i] = ConvertArg(raw[i], ps[i].ParameterType);
            var ret = best.Invoke(best.IsStatic ? null : obj, conv);
            return Result.Good("call " + name + " -> " + Fmt(ret));
        }

        static Result Coroutine(string[] args)
        {
            if (args.Length < 2) return Result.Bad("usage: coroutine <selector> <method> [args...]");
            object obj = Resolve(args[0]);
            if (obj == null) return Result.Bad("object not resolved: " + args[0]);
            var t = obj.GetType();
            string name = args[1];
            string[] raw = args.Skip(2).ToArray();
            MethodInfo best = null;
            for (Type cur = t; cur != null && best == null; cur = cur.BaseType)
            {
                foreach (var m in cur.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly))
                {
                    if (m.Name != name) continue;
                    if (m.GetParameters().Length != raw.Length) continue;
                    best = m; break;
                }
            }
            if (best == null) return Result.Bad("method not found: " + name + "/" + raw.Length + " on " + t.Name);
            var ps = best.GetParameters();
            var conv = new object[ps.Length];
            for (int i = 0; i < ps.Length; i++) conv[i] = ConvertArg(raw[i], ps[i].ParameterType);
            var ret = best.Invoke(best.IsStatic ? null : obj, conv);
            if (ret is IEnumerator)
            {
                var mb = obj as MonoBehaviour;
                if (mb == null) return Result.Bad("method returns IEnumerator but object is not a MonoBehaviour (got " + t.Name + ")");
                mb.StartCoroutine((IEnumerator)ret);
                return Result.Good("coroutine started " + name);
            }
            return Result.Good("call " + name + " -> " + Fmt(ret) + "  [not a coroutine]");
        }

        // ---------- capture / input ----------

        static Result Shot(string[] args)
        {
            string dir = Path.Combine(Application.dataPath, "..", "shots");
            Directory.CreateDirectory(dir);
            string name = args.Length > 0 ? args[0] : ("shot_" + DateTime.Now.ToString("HHmmss_fff"));
            if (!name.ToLower().EndsWith(".png")) name += ".png";
            string full = Path.GetFullPath(Path.Combine(dir, name));
            ScreenCapture.CaptureScreenshot(full);
            return Result.Good(full);
        }

        static Result Bytes(string[] args)
        {
            if (args.Length < 1) return Result.Bad("usage: bytes <path>");
            var fi = new FileInfo(args[0]);
            if (!fi.Exists) return Result.Bad("no file");
            return Result.Good("size=" + fi.Length + " mtime=" + fi.LastWriteTime.ToString("HH:mm:ss.fff"));
        }

        [DllImport("user32.dll")] static extern bool SetCursorPos(int x, int y);
        [DllImport("user32.dll")] static extern void mouse_event(uint flags, uint dx, uint dy, uint data, IntPtr extra);
        [DllImport("user32.dll")] static extern void keybd_event(byte vk, byte scan, uint flags, IntPtr extra);
        const uint LDOWN = 0x0002, LUP = 0x0004, RDOWN = 0x0008, RUP = 0x0010, KEYUP = 0x0002;

        static Result Mouse(string[] args)
        {
            // mouse <x> <y> <down|up|click|rclick|move>
            if (args.Length < 3) return Result.Bad("usage: mouse x y action");
            int x = (int)float.Parse(args[0]), y = (int)float.Parse(args[1]);
            string act = args[2];
            SetCursorPos(x, y);
            switch (act)
            {
                case "down": mouse_event(LDOWN, 0, 0, 0, IntPtr.Zero); break;
                case "up": mouse_event(LUP, 0, 0, 0, IntPtr.Zero); break;
                case "click":
                    mouse_event(LDOWN, 0, 0, 0, IntPtr.Zero);
                    mouse_event(LUP, 0, 0, 0, IntPtr.Zero);
                    break;
                case "rclick":
                    mouse_event(RDOWN, 0, 0, 0, IntPtr.Zero);
                    mouse_event(RUP, 0, 0, 0, IntPtr.Zero);
                    break;
                case "move": break;
                default: return Result.Bad("bad action " + act);
            }
            return Result.Good("mouse " + x + "," + y + " " + act);
        }

        static Result Key(string[] args)
        {
            if (args.Length < 1) return Result.Bad("usage: key <vk> [hold_ms]");
            byte vk = byte.Parse(args[0]);
            keybd_event(vk, 0, 0, IntPtr.Zero);
            keybd_event(vk, 0, KEYUP, IntPtr.Zero);
            return Result.Good("key " + vk);
        }

        [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr hWnd);
        [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr hWnd, int cmd);
        [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc cb, IntPtr p);
        [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
        [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr hWnd);
        delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);

        static IntPtr FindWindow(int pid)
        {
            IntPtr found = IntPtr.Zero;
            EnumWindows((h, l) =>
            {
                uint p; GetWindowThreadProcessId(h, out p);
                if (p == (uint)pid && IsWindowVisible(h)) { found = h; return false; }
                return true;
            }, IntPtr.Zero);
            return found;
        }

        static Result Focus(string[] args)
        {
            var pid = System.Diagnostics.Process.GetCurrentProcess().Id;
            var h = FindWindow(pid);
            if (h == IntPtr.Zero) return Result.Bad("window not found");
            ShowWindow(h, 9);          // SW_RESTORE
            bool ok = SetForegroundWindow(h);
            return Result.Good("hwnd=" + h + " foreground=" + ok + " wasFg=" + (GetForegroundWindow() == h));
        }

        static Result MoveCmd(string[] args, AgentPlugin plugin)
        {
            if (args.Length < 2) return Result.Bad("usage: move x y");
            int x = (int)float.Parse(args[0]), y = (int)float.Parse(args[1]);
            SetCursorPos(x, y);
            return Result.Good("move " + x + "," + y);
        }

        static Result BtnCmd(string a, string[] args, AgentPlugin plugin)
        {
            if (a == "down") mouse_event(LDOWN, 0, 0, 0, IntPtr.Zero); else mouse_event(LUP, 0, 0, 0, IntPtr.Zero);
            return Result.Good("button " + a);
        }

        static Result ClickCmd(string[] args, AgentPlugin plugin)
        {
            if (args.Length < 2) return Result.Bad("usage: click x y");
            int x = (int)float.Parse(args[0]), y = (int)float.Parse(args[1]);
            plugin.EnqueueAction(() => SetCursorPos(x, y));
            plugin.EnqueueAction(() => mouse_event(LDOWN, 0, 0, 0, IntPtr.Zero));
            plugin.EnqueueAction(() => mouse_event(LUP, 0, 0, 0, IntPtr.Zero));
            return Result.Good("queued click " + x + "," + y);
        }

        static Result DragCmd(string[] args, AgentPlugin plugin)
        {
            // drag x1 y1 x2 y2 [steps]
            if (args.Length < 4) return Result.Bad("usage: drag x1 y1 x2 y2 [steps]");
            float x1 = float.Parse(args[0]), y1 = float.Parse(args[1]);
            float x2 = float.Parse(args[2]), y2 = float.Parse(args[3]);
            int steps = args.Length > 4 ? int.Parse(args[4]) : 20;
            plugin.EnqueueAction(() => SetCursorPos((int)x1, (int)y1));
            plugin.EnqueueAction(() => mouse_event(LDOWN, 0, 0, 0, IntPtr.Zero));
            for (int i = 1; i <= steps; i++)
            {
                float t = (float)i / steps;
                int x = (int)(x1 + (x2 - x1) * t), y = (int)(y1 + (y2 - y1) * t);
                plugin.EnqueueAction(() => SetCursorPos(x, y));
            }
            plugin.EnqueueAction(() => mouse_event(LUP, 0, 0, 0, IntPtr.Zero));
            return Result.Good("queued drag " + x1 + "," + y1 + " -> " + x2 + "," + y2 + " steps=" + steps);
        }

        static Result ClickUi(string[] args)
        {
            if (args.Length < 1) return Result.Bad("usage: clickui <gameObjectPathOrName> [componentType]");
            string want = args[0];
            string typeName = args.Length > 1 ? args[1] : "UnityEngine.UI.Button";
            GameObject go = GameObject.Find(want);
            if (go == null)
            {
                string leaf = want.Contains("/") ? want.Substring(want.LastIndexOf('/') + 1) : want;
                foreach (var g in Resources.FindObjectsOfTypeAll<GameObject>())
                {
                    if (g.name == leaf && g.scene.IsValid()) { go = g; break; }
                }
            }
            if (go == null) return Result.Bad("gameObject not found: " + want);
            var t = ResolveType(typeName);
            if (t == null) return Result.Bad("component type not found: " + typeName);
            var comp = go.GetComponentsInChildren(t, true).FirstOrDefault() ?? go.GetComponent(t);
            if (comp == null) return Result.Bad("no " + typeName + " on " + want);
            var evtField = t.GetField("onClick", BindingFlags.Public | BindingFlags.Instance);
            object evt = evtField != null ? evtField.GetValue(comp) : null;
            if (evt == null)
            {
                var prop = t.GetProperty("onClick", BindingFlags.Public | BindingFlags.Instance);
                if (prop != null && prop.CanRead) evt = prop.GetValue(comp, null);
            }
            if (evt == null) return Result.Bad("no onClick event on " + t.Name);
            var inv = evt.GetType().GetMethod("Invoke", Type.EmptyTypes);
            if (inv == null) return Result.Bad("no Invoke on event");
            inv.Invoke(evt, null);
            return Result.Good("clicked ui " + GoPath(go.transform) + " via " + t.Name + ".onClick");
        }

        static Result InputProbe(string[] args)
        {
            var t = AllTypes().FirstOrDefault(x => x.FullName == "UnityEngine.Input");
            if (t == null) return Result.Bad("UnityEngine.Input type not found in loaded assemblies");
            var sb = new StringBuilder();
            sb.Append("assembly ").Append(t.Assembly.GetName().Name).Append('\n');
            foreach (var name in new[] { "mousePosition", "mousePresent", "anyKey", "mouseScrollDelta" })
            {
                var p = t.GetProperty(name, BindingFlags.Public | BindingFlags.Static);
                if (p == null) { sb.Append(name).Append(" <missing>\n"); continue; }
                try { sb.Append(name).Append(" = ").Append(Fmt(p.GetValue(null, null))).Append('\n'); }
                catch (Exception e) { sb.Append(name).Append(" ! ").Append(e.Message).Append('\n'); }
            }
            foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.Static).Where(m => m.Name == "GetMouseButton" || m.Name == "GetMouseButtonDown" || m.Name == "GetKeyDown"))
            {
                var ps = m.GetParameters();
                if (ps.Length != 1 || ps[0].ParameterType != typeof(int)) continue;
                foreach (var idx in new[] { 0, 1 })
                {
                    try { sb.Append(m.Name).Append('(').Append(idx).Append(") = ").Append(m.Invoke(null, new object[] { idx })).Append('\n'); }
                    catch (Exception) { }
                }
            }
            return Result.Good(sb.ToString());
        }

        static Result Log(string[] args)
        {
            int n = args.Length > 0 ? int.Parse(args[0]) : 40;
            string p = Path.Combine(Paths.BepInExRootPath, "LogOutput.log");
            if (!File.Exists(p)) return Result.Bad("no log");
            var lines = File.ReadAllLines(p);
            var tail = lines.Skip(Math.Max(0, lines.Length - n));
            return Result.Good(string.Join("\n", tail.ToArray()));
        }
    }
}
