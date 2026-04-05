procedure(SBhilightClearSet(hlSet)
  when(hlSet
    when(geIsValidHilightSet(hlSet)
      geDeleteHilightSetInWindows(hlSet)
      geDeleteHilightSet(hlSet)
    )
  )
)


procedure(SBmakeHilightSet(cv)
let((hlSet)
  hlSet = geCreateHilightSet(cv list("annotate" "drawing") nil)
  hlSet~>enable = t
  geSetHilightSetHaloParameters(hlSet "over" "fadeout" "normal" 30 nil)
  hlSet
)
)


procedure(SBaddObjectToHilightSet(hlSet obj)
let((added item)
  added = nil
  cond(
    (obj == nil
      nil
    )
    (listp(obj)
      foreach(item obj
        when(SBaddObjectToHilightSet(hlSet item)
          added = t
        )
      )
      added
    )
    (obj~>objType == "net"
      foreach(item obj~>figs
        when(SBaddObjectToHilightSet(hlSet item)
          added = t
        )
      )
      added
    )
    (or(obj~>objType == "inst" obj~>bBox)
      geAddHilightFig(hlSet obj)
      t
    )
    (t
      nil
    )
  )
)
)


procedure(SBhilightObjects(cv objects)
let((found)
  when(cv~>objType == "cellView"
    SBhilightClearSet(SBhilightObjects.hlSet)
    SBhilightObjects.hlSet = SBmakeHilightSet(cv)
    found = SBaddObjectToHilightSet(SBhilightObjects.hlSet objects)
    unless(found
      SBhilightClearSet(SBhilightObjects.hlSet)
      SBhilightObjects.hlSet = nil
    )
    found
  )
)
)


procedure(SBunhilightObjects()
  SBhilightClearSet(SBhilightObjects.hlSet)
  SBhilightObjects.hlSet = nil
)


procedure(SBfindInstByName(cv instName)
let((instObj found)
  found = nil
  foreach(instObj cv~>instances
    when(equal(instObj~>name instName)
      found = instObj
    )
  )
  found
)
)


procedure(SBfindObjectByName(cv objName)
let((netObj instObj)
  when(and(cv~>objType == "cellView" not(blankstrp(objName)))
    netObj = dbFindNetByName(cv objName)
    instObj = nil
    unless(netObj
      instObj = SBfindInstByName(cv objName)
    )
    if(netObj
      netObj
      instObj
    )
  )
)
)


procedure(SBfindInstsByName(cv instNames)
let((instObj found)
  found = nil
  foreach(instObj cv~>instances
    when(member(instObj~>name instNames 'equal)
      found = cons(instObj found)
    )
  )
  reverse(found)
)
)


procedure(SBhilightNets(cv netName "dt")
let((netObj)
  when(and(cv~>objType == "cellView" not(blankstrp(netName)))
    when(netObj = dbFindNetByName(cv netName)
      SBhilightObjects(cv netObj)
    )
  )
)
)


procedure(SBunhilightNets()
  SBunhilightObjects()
)


procedure(SBhilightInsts(cv instName "dt")
let((instObj)
  when(and(cv~>objType == "cellView" not(blankstrp(instName)))
    when(instObj = SBfindInstByName(cv instName)
      SBhilightObjects(cv instObj)
    )
  )
)
)


procedure(SBhilightInstList(cv instNames)
  when(cv~>objType == "cellView"
    SBhilightObjects(cv SBfindInstsByName(cv instNames))
  )
)


procedure(SBunhilightInsts()
  SBunhilightObjects()
)


procedure(SBclearStuckInstHalo(cv instNames)
let((insts instName instObj)
  insts = nil
  when(cv~>objType == "cellView"
    foreach(instName instNames
      instObj = SBfindInstByName(cv instName)
      when(instObj
        insts = cons(instObj insts)
      )
    )
    when(insts
      geUnsetSelProtection(reverse(insts))
    )
    geUnhighlightProtected(hiGetCurrentWindow())
    geDeleteAllWindowHilightSet(hiGetCurrentWindow())
  )
)
)


;load "/home/cloud/projects/skillbridge/examples/highlight_net.il"
;SBhilightObjects(geGetEditCellView() dbFindNetByName(geGetEditCellView() "bias1"))
;SBhilightObjects(geGetEditCellView() SBfindInstByName(geGetEditCellView() "NM1"))
;SBhilightObjects(geGetEditCellView() list(dbFindNetByName(geGetEditCellView() "bias1") SBfindInstByName(geGetEditCellView() "NM1")))
;SBunhilightObjects()
;SBclearStuckInstHalo(geGetEditCellView() list("NM1" "PM1"))
