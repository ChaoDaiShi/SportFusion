using System;
using System.Diagnostics;
using System.Linq;

internal static class SofficeWait
{
    private const string Program = @"F:\LibreOffice\LibreOfficePortable\App\libreoffice\program\soffice.com";

    private static string Quote(string value)
    {
        return "\"" + value.Replace("\"", "\\\"") + "\"";
    }

    private static string Normalize(string value)
    {
        const string prefix = "-env:UserInstallation=file://";
        if (value.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
        {
            var path = value.Substring(prefix.Length).Replace('\\', '/');
            if (path.Length > 2 && path[1] == ':')
            {
                return prefix + "/" + path;
            }
        }
        return value;
    }

    public static int Main(string[] args)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = Program,
            Arguments = string.Join(" ", args.Select(Normalize).Select(Quote)),
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = false,
            RedirectStandardError = false,
            WorkingDirectory = System.IO.Path.GetDirectoryName(Program)
        };
        using (var process = Process.Start(startInfo))
        {
            process.WaitForExit();
            return process.ExitCode;
        }
    }
}
