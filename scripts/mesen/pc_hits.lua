-- Log the frame of each execution (first 20 per PC) of a list of PCs while playing ROUTE from FROM.
-- Params: FROM (optional), ROUTE, NAME, PCS ("8093E1,828000,...").
local hits = {}
local function begin()
  for hex in tostring(PCS):gmatch("[^,]+") do
    local pc = tonumber(hex, 16)
    hits[pc] = {}
    emu.addMemoryCallback(function()
      local t = hits[pc]
      if #t < 20 then t[#t + 1] = L.frame end
    end, emu.callbackType.exec, pc, pc, emu.cpuType.snes, emu.memType.snesMemory)
  end
  L.load_route(ROUTE)
  L.on_frame(function()
    if L.route_done() then
      local out = {}
      for pc, t in pairs(hits) do
        local fs = {}
        for _, f in ipairs(t) do fs[#fs + 1] = tostring(f) end
        out[#out + 1] = string.format("%06X %s", pc, table.concat(fs, " "))
      end
      table.sort(out)
      L.write_file("trace/pc_hits_" .. NAME .. ".txt", table.concat(out, "\n") .. "\n")
      L.finish(0)
    end
  end)
end
if FROM then L.load_state(FROM, begin) else begin() end
