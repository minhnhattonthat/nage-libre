-- Shared helpers. The runner prepends WORK (abs path, trailing /) and params.
L = { frame = 0 }
local snes, cpuMem = emu.cpuType.snes, emu.memType.snesMemory

-- PRG-ROM memory callbacks receive the CPU address (LoROM); convert to file offset.
function L.rom_off(a) return ((a & 0x7F0000) >> 1) | (a & 0x7FFF) end
function L.path(rel) return WORK .. rel end
function L.write_file(rel, data) local f = assert(io.open(WORK .. rel, "wb")); f:write(data); f:close() end
function L.read_file(rel) local f = assert(io.open(WORK .. rel, "rb")); local d = f:read("a"); f:close(); return d end
function L.shot(rel) L.write_file(rel, emu.takeScreenshot()) end
function L.finish(code) emu.stop(code or 0) end
function L.fail(msg)
  local f = io.open(ERRFILE or (WORK .. "lua_error.txt"), "a"); f:write(tostring(msg) .. "\n"); f:close()
  emu.stop(2)
end
-- Wrap a callback so Lua errors stop the run and land in work/lua_error.txt. Returns nothing.
function L.safe(fn) return function(...) local ok, e = pcall(fn, ...); if not ok then L.fail(e) end end end

-- Register writes: hook bank $00 and $80 mirrors.
function L.on_reg_write(reg, fn)
  for _, bank in ipairs({0x000000, 0x800000}) do
    emu.addMemoryCallback(L.safe(fn), emu.callbackType.write, bank + reg, bank + reg, snes, cpuMem)
  end
end

function L.dump_mem(mem, size, rel)
  local t = {}
  for i = 0, size - 1 do t[#t + 1] = string.char(emu.read(i, mem)) end
  L.write_file(rel, table.concat(t))
end

-- Savestates only work inside an exec callback: queue jobs, run them on the next instruction.
local jobs, execId = {}, nil
local function service()
  local job = table.remove(jobs, 1)
  if not job then return end
  if job.op == "save" then
    L.write_file("states/" .. job.name .. ".mss", emu.createSavestate())
  else
    emu.loadSavestate(L.read_file("states/" .. job.name .. ".mss"))
  end
  if #jobs == 0 then
    emu.removeMemoryCallback(execId, emu.callbackType.exec, 0, 0xFFFFFF, snes, cpuMem)
    execId = nil
  end
  if job.done then job.done() end
end
local function schedule(job)
  jobs[#jobs + 1] = job
  if not execId then
    execId = emu.addMemoryCallback(L.safe(service), emu.callbackType.exec, 0, 0xFFFFFF, snes, cpuMem)
  end
end
function L.save_state(name, done) schedule({ op = "save", name = name, done = done }) end
function L.load_state(name, done) schedule({ op = "load", name = name, done = done }) end

-- Input queue: entries {buttons, frames}. spec is "-" or "a+start+up".
local queue = {}
function L.press(spec, frames)
  local b = {}
  if spec ~= "-" then for name in spec:gmatch("[^+]+") do b[name] = true end end
  queue[#queue + 1] = { buttons = b, frames = frames }
end
function L.load_route(path)
  for line in io.lines(path) do
    local l = line:gsub("#.*", ""):match("^%s*(.-)%s*$")
    if l ~= "" then
      local n, spec = l:match("^(%d+)%s+(%S+)$")
      if not n then error("bad route line: " .. line) end
      L.press(spec, tonumber(n))
    end
  end
end
function L.route_done() return #queue == 0 end
emu.addEventCallback(L.safe(function()
  local q = queue[1]
  if q then emu.setInput(q.buttons, 0) end
end), emu.eventType.inputPolled)

local frameFns = {}
function L.on_frame(fn) frameFns[#frameFns + 1] = fn end
emu.addEventCallback(L.safe(function()
  L.frame = L.frame + 1
  local q = queue[1]
  if q then q.frames = q.frames - 1; if q.frames <= 0 then table.remove(queue, 1) end end
  for _, fn in ipairs(frameFns) do fn(L.frame) end
end), emu.eventType.endFrame)
