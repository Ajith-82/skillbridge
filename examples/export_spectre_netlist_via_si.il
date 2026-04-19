procedure(sbWriteLinesToFile(path lines)
  let((port line)
    port = outfile(path)
    unless(port
      error("Could not open %s for writing.\n" path)
    )
    foreach(line lines
      fprintf(port "%s\n" line)
    )
    close(port)
    path
  )
)


procedure(sbShellQuote(text)
  strcat("'" buildString(parseString(text "'") "'\"'\"'") "'")
)


procedure(sbPrintFileTail(path @optional (lineCount 40))
  let((port line (lines declare(lines[lineCount])) (ptr 0) (count 0) limit start idx)
    port = infile(path)
    if(port then
      prog( ()
        while(gets(line port)
          lines[ptr] = line
          ptr = mod(ptr + 1 lineCount)
          count = count + 1
        )
        close(port)
        limit = min(count lineCount)
        start = if(count < lineCount then 0 else ptr)
        for(idx 0 limit - 1
          printf("%s" lines[mod(start + idx lineCount)])
        )
        t
      )
      printf("sbPrintFileTail: could not open %s\n" path)
      nil
    )
  )
)


procedure(sbWriteSiEnv(runDir libName cellName viewName
                       @key
                       (configName nil)
                       (versionName "")
                       (simulator "spectre")
                       (notIncremental nil)
                       (reNetlistAll t)
                       (viewList '("spectre" "schematic" "symbol"))
                       (stopList '("spectre"))
                       (netlistHier t))
  let((lines siEnvPath)
    siEnvPath = strcat(runDir "/si.env")
    lines = list(
      lsprintf("simLibName = %L" libName)
      lsprintf("simLibConfigName = %s" if(configName then lsprintf("%L" configName) else "nil"))
      lsprintf("simCellName = %L" cellName)
      lsprintf("simViewName = %L" viewName)
      lsprintf("simVersionName = %L" versionName)
      lsprintf("simSimulator = %L" simulator)
      lsprintf("simNotIncremental = %L" notIncremental)
      lsprintf("simReNetlistAll = %L" reNetlistAll)
      lsprintf("simViewList = '%L" viewList)
      lsprintf("simStopList = '%L" stopList)
    )
    when(netlistHier
      lines = append(lines list(lsprintf("simNetlistHier = %L" netlistHier)))
    )
    sbWriteLinesToFile(siEnvPath lines)
  )
)


procedure(sbRunSiNetlist(runDir
                         @key
                         (cdsLibPath strcat(runDir "/cds.lib"))
                         (siBinary "/opt/cadence/IC231/bin/si")
                         (command "nl")
                         (logFileName "si.stdout.log")
                         (tailLines 80))
  let((logPath shellFragment shellCommand exitCode inputPath netlistPath)
    logPath = strcat(runDir "/" logFileName)
    shellFragment = lsprintf(
      "cd %s && %s -batch -command %s -cdslib %s > %s 2>&1"
      sbShellQuote(runDir)
      sbShellQuote(siBinary)
      sbShellQuote(command)
      sbShellQuote(cdsLibPath)
      sbShellQuote(logPath)
    )
    shellCommand = strcat("/bin/sh -c " sbShellQuote(shellFragment))
    printf("sbRunSiNetlist command:\n%s\n" shellCommand)
    exitCode = system(shellCommand)
    printf("sbRunSiNetlist exit code: %L\n" exitCode)
    printf("sbRunSiNetlist log tail (%s):\n" logPath)
    sbPrintFileTail(logPath tailLines)
    inputPath = strcat(runDir "/input.scs")
    netlistPath = strcat(runDir "/netlist")
    list(nil
      'exitCode exitCode
      'runDir runDir
      'cdsLibPath cdsLibPath
      'siEnvPath strcat(runDir "/si.env")
      'logPath logPath
      'inputPath inputPath
      'netlistPath netlistPath
    )
  )
)


procedure(sbExportSpectreNetlist(runDir cdsLibPath libName cellName viewName
                                 @key
                                 (configName nil)
                                 (versionName "")
                                 (simulator "spectre")
                                 (notIncremental nil)
                                 (reNetlistAll t)
                                 (viewList '("spectre" "schematic" "symbol"))
                                 (stopList '("spectre"))
                                 (netlistHier t)
                                 (siBinary "/opt/cadence/IC231/bin/si")
                                 (command "nl")
                                 (logFileName "si.stdout.log")
                                 (tailLines 80))
  sbWriteSiEnv(runDir libName cellName viewName
    ?configName configName
    ?versionName versionName
    ?simulator simulator
    ?notIncremental notIncremental
    ?reNetlistAll reNetlistAll
    ?viewList viewList
    ?stopList stopList
    ?netlistHier netlistHier
  )
  sbRunSiNetlist(runDir
    ?cdsLibPath cdsLibPath
    ?siBinary siBinary
    ?command command
    ?logFileName logFileName
    ?tailLines tailLines
  )
)
