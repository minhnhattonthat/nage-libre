-- Birthstone-bonus QA hook for the skill's emu.py (uses its L.* driver, not lib.lua). Logs every battle bonus /
-- attack-line print and screenshots OFFS frames after each bonus. Cold boot, first battle bonus at ~f10495:
--   emu.py build/nage_en.sfc --out work/qa/bonus --route scripts/mesen/routes/new_game_mash.txt --mash 20
--          --frames 11200 --shot-every 0 --script <this file, optionally with lines prepended>
-- Optional globals (prepend lines): FORCE_BONUS = true (make card jewel = birthstone at every check), MAX_HITS,
-- OFFS = {frames...}, NAME_A / NAME_B = name index for enemy ($109C) / player ($1084) = system entry + 1
-- (0xE1 Tsukiyomi, 0x89 Sakurako: the widest names).
local M = emu.memType.snesMemory
local function r16(a) return emu.read(a, M) | (emu.read(a + 1, M) << 8) end
local function w16(a, v) emu.write(a, v & 0xFF, M); emu.write(a + 1, v >> 8, M) end
local pending = {}
local hits = 0
local sites = { [0x819988] = "258 dmg(E)", [0x819A20] = "258 dmg(P)", [0x819AA8] = "275 def(P)", [0x819B12] = "275 def(E)",
                [0x819B7C] = "275 heal(P)", [0x819BE6] = "275 heal(E)", [0x8198A4] = "attack line", [0x8198CA] = "super line" }
for a, name in pairs(sites) do
  L.on_exec(a, a, function()
    L.log(string.format("f%d %s 10B0=%04X 10B2=%04X 10C8=%04X 10E8=%04X 10C2=%04X 10E2=%04X 1084=%04X 109C=%04X cur=%04X",
      L.frame, name, r16(0x10B0), r16(0x10B2), r16(0x10C8), r16(0x10E8), r16(0x10C2), r16(0x10E2), r16(0x1084), r16(0x109C), r16(0x1141)))
    if name:sub(1, 3) == "258" or name:sub(1, 3) == "275" then
      hits = hits + 1
      if hits <= (MAX_HITS or 3) then
        for _, d in ipairs((OFFS or { 2, 20, 45, 70, 100, 140 })) do pending[L.frame + d] = string.format("bonus%d_%s_+%03d.png", hits, name:sub(1, 3), d) end
      end
    end
  end)
end
if FORCE_BONUS then
  -- at "lda $10E8 / cmp $10B2" (enemy) and "lda $10C8 / cmp $10B0" (player): make the jewels match
  for _, a in ipairs({ 0x81996E, 0x819BCC }) do L.on_exec(a, a, function() w16(0x10E8, r16(0x10B2)) end) end
  for _, a in ipairs({ 0x819A06, 0x819B62 }) do L.on_exec(a, a, function() w16(0x10C8, r16(0x10B0)) end) end
end
if NAME_A or NAME_B then
  -- battle name indexes ($109C / $1084) feed the message-line name printer 819D19
  L.on_frame(function() if NAME_A then w16(0x109C, NAME_A) end; if NAME_B then w16(0x1084, NAME_B) end end)
end
L.on_frame(function(f) local p = pending[f]; if p then L.shot(p); pending[f] = nil end end)
