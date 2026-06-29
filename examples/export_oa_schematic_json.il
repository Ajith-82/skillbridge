procedure(sbOaJsonObj(pairs)
  list('obj pairs)
)

procedure(sbOaJsonArr(items)
  list('arr items)
)

procedure(sbOaJsonPair(key value)
  list(key value)
)

procedure(sbOaWriteIndent(port indent)
  let((i)
    for(i 1 indent
      fprintf(port " ")
    )
  )
)

procedure(sbOaWriteJsonValue(port value indent)
  cond(
    (stringp(value)
      fprintf(port "%L" value)
    )
    (numberp(value)
      fprintf(port "%L" value)
    )
    (value == t
      fprintf(port "true")
    )
    (value == nil
      fprintf(port "null")
    )
    (and(listp(value) car(value) == 'obj)
      sbOaWriteJsonObject(port cadr(value) indent)
    )
    (and(listp(value) car(value) == 'arr)
      sbOaWriteJsonArray(port cadr(value) indent)
    )
    (t
      fprintf(port "%L" sprintf(nil "%L" value))
    )
  )
)

procedure(sbOaWriteJsonObject(port pairs indent)
  let((first pair)
    fprintf(port "{")
    first = t
    foreach(pair pairs
      unless(first
        fprintf(port ",")
      )
      first = nil
      fprintf(port "\n")
      sbOaWriteIndent(port indent + 2)
      fprintf(port "%L: " car(pair))
      sbOaWriteJsonValue(port cadr(pair) indent + 2)
    )
    unless(first
      fprintf(port "\n")
      sbOaWriteIndent(port indent)
    )
    fprintf(port "}")
  )
)

procedure(sbOaWriteJsonArray(port items indent)
  let((first item)
    fprintf(port "[")
    first = t
    foreach(item items
      unless(first
        fprintf(port ",")
      )
      first = nil
      fprintf(port "\n")
      sbOaWriteIndent(port indent + 2)
      sbOaWriteJsonValue(port item indent + 2)
    )
    unless(first
      fprintf(port "\n")
      sbOaWriteIndent(port indent)
    )
    fprintf(port "]")
  )
)

procedure(sbOaNormalizeValue(value)
  cond(
    (stringp(value) value)
    (numberp(value) value)
    (value == t t)
    (value == nil nil)
    (t sprintf(nil "%L" value))
  )
)

procedure(sbOaStringMemberP(name strList)
  let((found item)
    found = nil
    foreach(item strList
      when(equal(item name)
        found = t
      )
    )
    found
  )
)

procedure(sbOaAppendPair(pairs key value)
  append(pairs list(sbOaJsonPair(key value)))
)

procedure(sbOaIrObjField(irObj key)
  let((pairs pair value)
    value = nil
    when(and(listp(irObj) car(irObj) == 'obj)
      pairs = cadr(irObj)
      foreach(pair pairs
        when(equal(car(pair) key)
          value = cadr(pair)
        )
      )
    )
    value
  )
)

procedure(sbOaSortKey(value)
  if(value sprintf(nil "%L" value) "")
)

procedure(sbOaStableInsertByField(item items fieldName)
  let((itemKey result inserted existing existingKey)
    itemKey = sbOaSortKey(sbOaIrObjField(item fieldName))
    result = nil
    inserted = nil
    foreach(existing items
      existingKey = sbOaSortKey(sbOaIrObjField(existing fieldName))
      when(and(not(inserted) alphalessp(itemKey existingKey))
        result = append(result list(item))
        inserted = t
      )
      result = append(result list(existing))
    )
    unless(inserted
      result = append(result list(item))
    )
    result
  )
)

procedure(sbOaStableSortByField(items fieldName)
  let((sorted item)
    sorted = nil
    foreach(item items
      sorted = sbOaStableInsertByField(item sorted fieldName)
    )
    sorted
  )
)

procedure(sbOaMakeCdfRef(libName cellName)
  sprintf(nil "%s/%s" libName cellName)
)

procedure(sbOaExcludedPdkCellP(libName cellName)
  or(
    and(equal(libName "basic") equal(cellName "ipin"))
    and(equal(libName "basic") equal(cellName "opin"))
  )
)

procedure(sbOaSchematicPinInstP(inst)
  let((master)
    master = inst~>master
    and(
      master
      equal(master~>libName "basic")
      member(master~>cellName list("ipin" "opin"))
    )
  )
)

procedure(sbOaPropToIr(prop)
  sbOaJsonObj(
    list(
      sbOaJsonPair("name" sbOaNormalizeValue(prop~>name))
      sbOaJsonPair("value" sbOaNormalizeValue(prop~>value))
      sbOaJsonPair("valueType" sbOaNormalizeValue(prop~>valueType))
    )
  )
)

procedure(sbOaCollectProps(obj)
  let((items prop)
    items = nil
    foreach(prop obj~>prop
      items = cons(sbOaPropToIr(prop) items)
    )
    sbOaJsonArr(reverse(items))
  )
)

procedure(sbOaCdfParamToIr(param)
  sbOaJsonObj(
    list(
      sbOaJsonPair("name" sbOaNormalizeValue(param~>name))
      sbOaJsonPair("value" sbOaNormalizeValue(param~>value))
    )
  )
)

procedure(sbOaCellCdfParamToIr(param)
  sbOaJsonObj(
    list(
      sbOaJsonPair("name" sbOaNormalizeValue(param~>name))
      sbOaJsonPair("defaultValue" sbOaNormalizeValue(param~>defValue))
      sbOaJsonPair("prompt" sbOaNormalizeValue(param~>prompt))
      sbOaJsonPair("type" sbOaNormalizeValue(param~>type))
      sbOaJsonPair("paramType" sbOaNormalizeValue(param~>paramType))
      sbOaJsonPair("units" sbOaNormalizeValue(param~>units))
      sbOaJsonPair("display" sbOaNormalizeValue(param~>display))
      sbOaJsonPair("callback" sbOaNormalizeValue(param~>callback))
    )
  )
)

procedure(sbOaGetCellCdf(master)
  let((cellObj)
    cellObj = ddGetObj(master~>libName master~>cellName)
    if(cellObj
      cdfGetCellCDF(cellObj)
      nil
    )
  )
)

procedure(sbOaCollectCellCdfParams(master)
  let((cdf items param)
    items = nil
    cdf = sbOaGetCellCdf(master)
    when(cdf
      foreach(param cdf~>parameters
        items = cons(sbOaCellCdfParamToIr(param) items)
      )
    )
    sbOaJsonArr(reverse(items))
  )
)

procedure(sbOaCollectCdfParams(inst)
  let((cdf cellCdf cellParam items param)
    items = nil
    cdf = cdfGetInstCDF(inst)
    cellCdf = nil
    when(inst~>master
      cellCdf = sbOaGetCellCdf(inst~>master)
    )
    when(cdf
      foreach(param cdf~>parameters
        cellParam = if(cellCdf cdfFindParamByName(cellCdf param~>name) nil)
        unless(and(cellParam equal(sbOaNormalizeValue(param~>value) sbOaNormalizeValue(cellParam~>defValue)))
          items = cons(sbOaCdfParamToIr(param) items)
        )
      )
    )
    sbOaJsonArr(reverse(items))
  )
)

procedure(sbOaPdkDeviceCdfToIr(master)
  sbOaJsonObj(
    list(
      sbOaJsonPair("cdfRef" sbOaMakeCdfRef(master~>libName master~>cellName))
      sbOaJsonPair("libName" sbOaNormalizeValue(master~>libName))
      sbOaJsonPair("cellName" sbOaNormalizeValue(master~>cellName))
      sbOaJsonPair("viewName" sbOaNormalizeValue(master~>viewName))
      sbOaJsonPair("parameters" sbOaCollectCellCdfParams(master))
    )
  )
)

procedure(sbOaCollectPdkDeviceCdfs(cv pdkLibs)
  let((items seen inst master cdfRef)
    items = nil
    seen = nil
    foreach(inst cv~>instances
      when(sbOaIsPdkInst(inst pdkLibs)
        master = inst~>master
        cdfRef = sbOaMakeCdfRef(master~>libName master~>cellName)
        unless(sbOaStringMemberP(cdfRef seen)
          seen = cons(cdfRef seen)
          items = cons(sbOaPdkDeviceCdfToIr(master) items)
        )
      )
    )
    sbOaJsonArr(sbOaStableSortByField(reverse(items) "cdfRef"))
  )
)

procedure(sbOaTerminalToIr(term)
  let((net)
    net = term~>net
    sbOaJsonObj(
      list(
        sbOaJsonPair("name" sbOaNormalizeValue(term~>name))
        sbOaJsonPair("direction" sbOaNormalizeValue(term~>direction))
        sbOaJsonPair("netName" if(net sbOaNormalizeValue(net~>name) nil))
      )
    )
  )
)

procedure(sbOaCollectPins(cv)
  let((items term)
    items = nil
    foreach(term cv~>terminals
      items = cons(sbOaTerminalToIr(term) items)
    )
    sbOaJsonArr(sbOaStableSortByField(reverse(items) "name"))
  )
)

procedure(sbOaInstTermToIr(instTerm)
  let((net term)
    net = instTerm~>net
    term = instTerm~>term
    sbOaJsonObj(
      list(
        sbOaJsonPair("termName" sbOaNormalizeValue(term~>name))
        sbOaJsonPair("direction" sbOaNormalizeValue(term~>direction))
        sbOaJsonPair("netName" if(net sbOaNormalizeValue(net~>name) nil))
      )
    )
  )
)

procedure(sbOaCollectInstConnections(inst)
  let((items instTerm)
    items = nil
    foreach(instTerm inst~>instTerms
      items = cons(sbOaInstTermToIr(instTerm) items)
    )
    sbOaJsonArr(reverse(items))
  )
)

procedure(sbOaMasterTermsToIr(master)
  let((items term)
    items = nil
    foreach(term master~>terminals
      items = cons(
        sbOaJsonObj(
          list(
            sbOaJsonPair("name" sbOaNormalizeValue(term~>name))
            sbOaJsonPair("direction" sbOaNormalizeValue(term~>direction))
          )
        )
        items
      )
    )
    sbOaJsonArr(reverse(items))
  )
)

procedure(sbOaIsPdkInst(inst pdkLibs)
  let((master)
    master = inst~>master
    and(
      master
      sbOaStringMemberP(master~>libName pdkLibs)
      not(sbOaExcludedPdkCellP(master~>libName master~>cellName))
    )
  )
)

procedure(sbOaInstanceToIr(inst pdkLibs)
  let((master kind cdfRef pairs)
    master = inst~>master
    kind = if(sbOaIsPdkInst(inst pdkLibs) "pdkDevice" "blackBox")
    cdfRef = if(and(master kind == "pdkDevice") sbOaMakeCdfRef(master~>libName master~>cellName) nil)
    pairs = nil
    pairs = sbOaAppendPair(pairs "name" sbOaNormalizeValue(inst~>name))
    pairs = sbOaAppendPair(pairs "kind" kind)
    pairs = sbOaAppendPair(pairs "cdfRef" cdfRef)
    pairs = sbOaAppendPair(pairs "libName" if(master sbOaNormalizeValue(master~>libName) nil))
    pairs = sbOaAppendPair(pairs "cellName" if(master sbOaNormalizeValue(master~>cellName) nil))
    pairs = sbOaAppendPair(pairs "viewName" if(master sbOaNormalizeValue(master~>viewName) nil))
    pairs = sbOaAppendPair(pairs "isPCell" if(master master~>isParamCell nil))
    pairs = sbOaAppendPair(pairs "connections" sbOaCollectInstConnections(inst))
    pairs = sbOaAppendPair(pairs "parameters" if(kind == "pdkDevice" sbOaCollectCdfParams(inst) sbOaJsonArr(nil)))
    pairs = sbOaAppendPair(pairs "rawProps" if(kind == "pdkDevice" sbOaJsonArr(nil) sbOaCollectProps(inst)))
    pairs = sbOaAppendPair(pairs "masterTerminals" if(master sbOaMasterTermsToIr(master) sbOaJsonArr(nil)))
    sbOaJsonObj(pairs)
  )
)

procedure(sbOaCollectInstances(cv pdkLibs)
  let((items inst)
    items = nil
    foreach(inst cv~>instances
      unless(sbOaSchematicPinInstP(inst)
        items = cons(sbOaInstanceToIr(inst pdkLibs) items)
      )
    )
    sbOaJsonArr(sbOaStableSortByField(reverse(items) "name"))
  )
)

procedure(sbOaNetConnInstTermToIr(instTerm)
  let((inst term)
    inst = instTerm~>inst
    term = instTerm~>term
    sbOaJsonObj(
      list(
        sbOaJsonPair("kind" "instTerm")
        sbOaJsonPair("instName" if(inst sbOaNormalizeValue(inst~>name) nil))
        sbOaJsonPair("termName" if(term sbOaNormalizeValue(term~>name) nil))
        sbOaJsonPair("direction" if(term sbOaNormalizeValue(term~>direction) nil))
      )
    )
  )
)

procedure(sbOaNetConnTerminalToIr(term)
  sbOaJsonObj(
    list(
      sbOaJsonPair("name" sbOaNormalizeValue(term~>name))
      sbOaJsonPair("direction" sbOaNormalizeValue(term~>direction))
    )
  )
)

procedure(sbOaCollectNetInstConnections(net)
  let((items instTerm term)
    items = nil
    foreach(instTerm net~>instTerms
      items = cons(sbOaNetConnInstTermToIr(instTerm) items)
    )
    sbOaJsonArr(reverse(items))
  )
)

procedure(sbOaCollectNetPinConnections(cv net)
  let((items term)
    items = nil
    foreach(term cv~>terminals
      when(term~>net == net
        items = cons(sbOaNetConnTerminalToIr(term) items)
      )
    )
    sbOaJsonArr(reverse(items))
  )
)

procedure(sbOaNetToIr(cv net)
  sbOaJsonObj(
    list(
      sbOaJsonPair("name" sbOaNormalizeValue(net~>name))
      sbOaJsonPair("instConnections" sbOaCollectNetInstConnections(net))
      sbOaJsonPair("pinConnections" sbOaCollectNetPinConnections(cv net))
      sbOaJsonPair("rawProps" sbOaCollectProps(net))
    )
  )
)

procedure(sbOaCollectNets(cv)
  let((items net)
    items = nil
    foreach(net cv~>nets
      items = cons(sbOaNetToIr(cv net) items)
    )
    sbOaJsonArr(sbOaStableSortByField(reverse(items) "name"))
  )
)

procedure(sbOaBuildIr(cv pdkLibs)
  sbOaJsonObj(
    list(
      sbOaJsonPair(
        "exporter"
        sbOaJsonObj(
          list(
            sbOaJsonPair("name" "oa_schematic_exporter")
            sbOaJsonPair("version" "v1")
          )
        )
      )
      sbOaJsonPair(
        "cellView"
        sbOaJsonObj(
          list(
            sbOaJsonPair("libName" sbOaNormalizeValue(cv~>libName))
            sbOaJsonPair("cellName" sbOaNormalizeValue(cv~>cellName))
            sbOaJsonPair("viewName" sbOaNormalizeValue(cv~>viewName))
            sbOaJsonPair("mode" "read")
            sbOaJsonPair("rawProps" sbOaCollectProps(cv))
          )
        )
      )
      sbOaJsonPair("instances" sbOaCollectInstances(cv pdkLibs))
      sbOaJsonPair("pins" sbOaCollectPins(cv))
      sbOaJsonPair("pdkDeviceCdfs" sbOaCollectPdkDeviceCdfs(cv pdkLibs))
      sbOaJsonPair("nets" sbOaCollectNets(cv))
    )
  )
)

procedure(sbOaOpenCvRead(libName cellName viewName)
  let((cv alreadyOpen)
    alreadyOpen = dbFindOpenCellViewByName(libName cellName viewName)
    if(alreadyOpen
      list(alreadyOpen nil)
      prog( ()
        cv = dbOpenCellViewByType(libName cellName viewName "schematic" "r")
        if(cv
          list(cv t)
          nil
        )
      )
    )
  )
)

procedure(sbExportOaSchematicToJson(libName cellName viewName outFile @optional (pdkLibs nil))
  let((cvInfo cv openedHere ir port)
    cvInfo = sbOaOpenCvRead(libName cellName viewName)
    unless(cvInfo
      error("Cannot open %s/%s/%s in read mode.\n" libName cellName viewName)
    )

    cv = car(cvInfo)
    openedHere = cadr(cvInfo)
    ir = sbOaBuildIr(cv pdkLibs)

    port = outfile(outFile)
    unless(port
      when(openedHere
        dbClose(cv)
      )
      error("Cannot open output file: %s\n" outFile)
    )

    sbOaWriteJsonValue(port ir 0)
    fprintf(port "\n")
    close(port)

    when(openedHere
      dbClose(cv)
    )

    outFile
  )
)

; load "/home/cloud/projects/skillbridge/examples/export_oa_schematic_json.il"
; sbExportOaSchematicToJson(
;   "myLib"
;   "myCell"
;   "schematic"
;   "/tmp/myCell.json"
;   list("tsmcN28" "analogLib" "basic")
; )
