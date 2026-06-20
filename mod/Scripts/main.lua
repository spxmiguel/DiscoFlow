-- DiscoFlow — Dead as Disco music integration mod
-- Requires UE4SS with ImGui support

local ui = require("Scripts.ui")

-- Toggle UI with F6
RegisterKeyBind(Key.F6, function()
    ui.toggle()
end)

-- Hook into the Free Play screen to add a "Use Your Music" button.
-- This hooks the BP_FreePlayMenu widget's Tick so we can inject the button
-- next to the existing "Add My Music" button.
-- Adjust the class name if the game updates its Blueprint names.
local hooked = false
NotifyOnNewObject("/Script/Engine.World", function()
    if hooked then return end

    local ok = pcall(function()
        HookBPFunction(
            "/Game/UI/Menus/FreePlay/BP_FreePlayMenu.BP_FreePlayMenu_C:AddMyMusic_Clicked",
            function() end,       -- pre
            function() end        -- post — we inject our button via ImGui overlay instead
        )
    end)

    if ok then hooked = true end
end)

-- ImGui render loop
RegisterImGuiCallback(function()
    ui.draw()
end)

print("[DiscoFlow] Loaded. Press F6 to open Use Your Music.")
