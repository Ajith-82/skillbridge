load("/home/cloud/projects/skillbridge/examples/highlight_net.il")

let((cv netObj instObj)
  cv = geGetEditCellView()
  netObj = dbFindNetByName(cv "bias1")
  instObj = SBfindInstByName(cv "NM1")

  unless(SBhilightObjects(cv netObj)
    error("SBhilightObjects failed on net\n")
  )

  unless(SBhilightObjects(cv instObj)
    error("SBhilightObjects failed on instance\n")
  )

  unless(SBhilightObjects(cv list(netObj instObj))
    error("SBhilightObjects failed on mixed objects\n")
  )

  SBunhilightObjects()
  t
)
