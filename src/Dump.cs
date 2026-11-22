using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Mono.Cecil;

class Dump
{
    static string Vis(MethodDefinition m)
    {
        string s = "";
        if (m.IsPublic) s += "public "; else if (m.IsFamily) s += "protected "; else if (m.IsAssembly) s += "internal "; else if (m.IsPrivate) s += "private "; else s += "other ";
        if (m.IsStatic) s += "static ";
        if (m.IsVirtual) s += "virtual ";
        var ret = m.ReturnType;
        s += ret.FullName + " " + m.Name;
        s += "(" + string.Join(", ", m.Parameters.Select(p => p.ParameterType.FullName + " " + p.Name)) + ")";
        return s;
    }

    static void DumpType(TypeDefinition t, StreamWriter w, string indent)
    {
        w.WriteLine(indent + "TYPE " + t.FullName + " : " + (t.BaseType != null ? t.BaseType.FullName : "-"));
        if (t.IsEnum)
        {
            foreach (var f in t.Fields.Where(f => f.HasConstant))
                w.WriteLine(indent + "  ENUMVAL " + f.Name + " = " + f.Constant);
            return;
        }
        foreach (var f in t.Fields)
            w.WriteLine(indent + "  FIELD " + (f.IsStatic ? "static " : "") + f.FieldType.FullName + " " + f.Name);
        foreach (var p in t.Properties)
            w.WriteLine(indent + "  PROP " + p.PropertyType.FullName + " " + p.Name + " get=" + (p.GetMethod != null) + " set=" + (p.SetMethod != null));
        foreach (var m in t.Methods.Where(m => !m.IsGetter && !m.IsSetter && !m.IsAddOn && !m.IsRemoveOn))
            w.WriteLine(indent + "  METH " + Vis(m));
        foreach (var nt in t.NestedTypes)
            DumpType(nt, w, indent + "  ");
    }

    static void Main(string[] args)
    {
        try
        {
            string dll = args[0], outPath = args[1];
            var resolver = new DefaultAssemblyResolver();
            resolver.AddSearchDirectory(Path.GetDirectoryName(Path.GetFullPath(dll)));
            resolver.AddSearchDirectory(@"C:\Program Files (x86)\Steam\steamapps\common\Zen Trails\Zen Trails_Data\Managed");
            var asm = AssemblyDefinition.ReadAssembly(dll, new ReaderParameters { AssemblyResolver = resolver });
            using (var w = new StreamWriter(outPath, false, new UTF8Encoding(false)))
            {
                foreach (var t in asm.MainModule.Types)
                    DumpType(t, w, "");
            }
            Console.WriteLine("wrote " + outPath);
        }
        catch (Exception e)
        {
            Console.Error.WriteLine("ERR type=" + e.GetType().FullName);
            Console.Error.WriteLine("ERR msg=" + e.Message);
            Console.Error.WriteLine("ERR trace=" + e.StackTrace);
            for (Exception i = e.InnerException; i != null; i = i.InnerException)
                Console.Error.WriteLine("INNER " + i.GetType().FullName + ": " + i.Message);
        }
    }
}
