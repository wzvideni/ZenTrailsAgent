using System;
using System.IO;
using System.Linq;
using System.Text;
using Mono.Cecil;
using Mono.Cecil.Cil;

class DumpIL
{
    static void Main(string[] args)
    {
        string dll = args[0], typeName = args[1], methodName = args.Length > 2 ? args[2] : null;
        var resolver = new DefaultAssemblyResolver();
        resolver.AddSearchDirectory(Path.GetDirectoryName(Path.GetFullPath(dll)));
        var asm = AssemblyDefinition.ReadAssembly(dll, new ReaderParameters { AssemblyResolver = resolver });
        var type = asm.MainModule.Types.SelectMany(Flatten).FirstOrDefault(t => t.FullName == typeName || t.Name == typeName);
        if (type == null) { Console.Error.WriteLine("type not found"); return; }
        var methods = type.Methods.Where(m => methodName == null || m.Name == methodName).ToList();
        foreach (var m in methods)
        {
            Console.WriteLine("=== " + m.FullName);
            if (!m.HasBody) { Console.WriteLine("  (no body)"); continue; }
            foreach (var v in m.Body.Variables)
                Console.WriteLine("  local " + v.Index + " " + v.VariableType.FullName);
            foreach (var i in m.Body.Instructions)
                Console.WriteLine("  " + i.Offset.ToString("X4") + "  " + i.OpCode + " " + Format(i.Operand));
        }
    }

    static string Format(object o)
    {
        if (o == null) return "";
        var md = o as MemberReference;
        if (md != null) return md.DeclaringType.Name + "::" + md.Name;
        var s = o as string;
        if (s != null) return "\"" + s + "\"";
        return o.ToString();
    }

    static System.Collections.Generic.IEnumerable<TypeDefinition> Flatten(TypeDefinition t)
    {
        yield return t;
        foreach (var n in t.NestedTypes)
            foreach (var x in Flatten(n)) yield return x;
    }
}
