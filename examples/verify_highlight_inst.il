load("/home/cloud/projects/skillbridge/examples/highlight_net.il")

unless(SBhilightInsts(geGetEditCellView() "NM1")
  error("SBhilightInsts failed\n")
)

unless(SBhilightInstList(geGetEditCellView() list("NM1" "PM1"))
  error("SBhilightInstList failed\n")
)

SBunhilightInsts()
t
