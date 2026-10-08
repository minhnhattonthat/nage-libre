-- Dump VRAM, OAM, CGRAM and PPU state after WAIT frames from FROM.  Params: FROM, NAME, WAIT (default 2).
local wait = WAIT or 2
local function begin()
  local start = L.frame
  L.on_frame(function(f)
    if f - start < wait then return end
    L.dump_mem(emu.memType.snesVideoRam, 0x10000, "mem/" .. NAME .. "_vram.bin")
    L.dump_mem(emu.memType.snesSpriteRam, 0x220, "mem/" .. NAME .. "_oam.bin")
    L.dump_mem(emu.memType.snesCgRam, 0x200, "mem/" .. NAME .. "_cgram.bin")
    local s, out = emu.getState(), {}
    for k, v in pairs(s) do
      if string.find(k, "ppu") then out[#out + 1] = k .. "=" .. tostring(v) end
    end
    table.sort(out)
    L.write_file("mem/" .. NAME .. "_ppu.txt", table.concat(out, "\n") .. "\n")
    L.shot("shots/" .. NAME .. "_dump.png")
    L.finish(0)
  end)
end
L.load_state(FROM, begin)
