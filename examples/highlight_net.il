procedure(SBhilightNets(cv netName "dt")
let((netObj hlSet)
  when(cv~>objType == "cellView"
    when(hlSet = SBhilightNets.hlSet
      when(geIsValidHilightSet(hlSet)
        geDeleteHilightSet(hlSet)
      );
    )
    SBhilightNets.hlSet = geCreateHilightSet(cv list("annotate" "drawing") nil)
    SBhilightNets.hlSet~>enable = t
    geSetHilightSetHaloParameters( SBhilightNets.hlSet "over" "fadeout" "normal" 30 nil)
    unless(blankstrp(netName)
      when(netObj = dbFindNetByName(cv netName)
        foreach(fig netObj~>figs
          geAddHilightFig(SBhilightNets.hlSet fig)
        )
        t
      ); when net object
    ); when net name not blank
  ); when cellview
); let
); procedure


procedure(SBunhilightNets()
let((hlSet)
  when(hlSet = SBhilightNets.hlSet
    when(geIsValidHilightSet(hlSet)
      geDeleteHilightSet(hlSet)
    );when
    SBhilightNets.hlSet = nil
  );when
);let
);procedure

;load "/home/cloud/projects/skillbridge/examples/highlight_net.il"
;SBhilightNets(geGetEditCellView() "bias1")
;SBunhilightNets()
