-- DiscoFlow — Dead as Disco music integration mod
-- Backend starts automatically when the game launches. No config needed.

local ui = require("Scripts.ui")

-- ── auto-start backend ────────────────────────────────────────────────────────

local BACKEND_EXE = (os.getenv("LOCALAPPDATA") or "") .. "\\DiscoFlow\\discoflow-backend.exe"

local function is_backend_running()
    local handle = io.popen('tasklist /FI "IMAGENAME eq discoflow-backend.exe" 2>NUL')
    if not handle then return false end
    local out = handle:read("*a")
    handle:close()
    return out:find("discoflow%-backend%.exe") ~= nil
end

local function start_backend()
    if not is_backend_running() then
        os.execute('start /min "" "' .. BACKEND_EXE .. '"')
    end
end

start_backend()

-- ── Free Play hooks ───────────────────────────────────────────────────────────

NotifyOnNewObject("/Game/UI/Menus/FreePlay/BP_FreePlayMenu.BP_FreePlayMenu_C",
    function(obj)
        ExecuteWithDelay(200, function()
            ui.show()
        end)
    end
)

HookUObjectFinalizer("/Game/UI/Menus/FreePlay/BP_FreePlayMenu.BP_FreePlayMenu_C",
    function(obj)
        ui.hide()
    end
)

-- ── ImGui render loop ─────────────────────────────────────────────────────────

RegisterImGuiCallback(function()
    ui.draw()
end)
