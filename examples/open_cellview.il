procedure(sbOpenCellView(libName cellName viewName @optional (viewType viewName) (accessMode "r") (winSpec nil))
  let((cv win)
    cv = dbFindOpenCellViewByName(libName cellName viewName)
    when(cv
      win = geGetCellViewWindow(cv)
    )
    or(win deOpenCellView(libName cellName viewName viewType winSpec accessMode))
  )
)

procedure(sbOpenEtherAdcSchematic()
  sbOpenCellView("ether" "adc" "schematic" "schematic" "r")
)
