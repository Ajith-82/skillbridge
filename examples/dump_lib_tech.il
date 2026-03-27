procedure(sbDumpLibTechFile(libName dumpFile @optional (sectionList nil) (mode "w") (dumpEmptySectionHdrs t))
  let((libObj techFileId)
    libObj = ddGetObj(libName)
    unless(libObj
      error("Library not found: %s" libName)
    )
    techFileId = techGetTechFile(libObj)
    unless(techFileId
      error("Technology file not found for library: %s" libName)
    )
    tcDumpTechFile(techFileId dumpFile sectionList mode dumpEmptySectionHdrs)
  )
)

procedure(sbDumpEtherTechFile(dumpFile)
  sbDumpLibTechFile("ether" dumpFile)
)

procedure(sbDumpTechFileForMarkdown(libName dumpFile)
  sbDumpLibTechFile(libName dumpFile)
)
