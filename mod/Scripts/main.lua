-- DiscoFlow — Dead as Disco music integration mod
-- Opens automatically when the Free Play menu is loaded. No key required.

local ui = require("Scripts.ui")

-- Hook the Free Play widget construction so the overlay opens the moment
-- the player enters that screen. UE4SS calls this whenever a new object
-- of the matching class is created in the world.
NotifyOnNewObject("/Game/UI/Menus/FreePlay/BP_FreePlayMenu.BP_FreePlayMenu_C",
    function(obj)
        -- Small delay so the game finishes building the widget before we draw
        ExecuteWithDelay(200, function()
            ui.show()
        end)
    end
)

-- Hide when the player leaves Free Play (widget gets destroyed / GC'd)
-- We hook Destruct on the same class.
HookUObjectFinalizer("/Game/UI/Menus/FreePlay/BP_FreePlayMenu.BP_FreePlayMenu_C",
    function(obj)
        ui.hide()
    end
)

-- ImGui render loop — only draws when ui.visible is true
RegisterImGuiCallback(function()
    ui.draw()
end)
