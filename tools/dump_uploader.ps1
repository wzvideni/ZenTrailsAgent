Add-Type -Path "tools/Mono.Cecil.dll"
$asm = [Mono.Cecil.AssemblyDefinition]::ReadAssembly("C:/Program Files (x86)/Steam/steamapps/common/Zen Trails/Zen Trails_Data/Managed/Assembly-CSharp.dll")
$type = $asm.MainModule.Types | Where-Object { $_.Name -eq "Uploader" }
foreach ($m in $type.Methods) {
    Write-Host ("=== Method: " + $m.Name)
    if ($m.HasBody) {
        foreach ($i in $m.Body.Instructions) {
            Write-Host ("  {0:X4} {1} {2}" -f $i.Offset, $i.OpCode, $i.Operand)
        }
    }
}
