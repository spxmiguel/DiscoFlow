local ipc = require("Scripts.ipc")
local M = {}

local state = {
    visible = false,
    screen = "services",   -- services | search | results | playlists
    service = nil,
    query = "",
    tracks = {},
    playlists = {},
    services = {},
    status_msg = "",
}

-- ── helpers ──────────────────────────────────────────────────────────────────

local function set_status(msg)
    state.status_msg = msg
end

local function load_services()
    set_status("Detecting streaming apps...")
    ipc.send({ action = "detect" }, function(resp)
        state.services = resp.services or {}
        state.screen = "services"
        set_status("")
    end)
end

local function search(query)
    if not state.service or query == "" then return end
    set_status("Searching...")
    local action = state.service == "Spotify" and "spotify_search"
               or state.service == "Deezer"  and "deezer_search"
               or nil
    if not action then return end
    ipc.send({ action = action, query = query }, function(resp)
        state.tracks = resp.tracks or {}
        state.screen = "results"
        set_status(#state.tracks == 0 and "No results." or "")
    end)
end

local function load_playlists()
    if state.service ~= "Spotify" then return end
    set_status("Loading playlists...")
    ipc.send({ action = "spotify_playlists" }, function(resp)
        state.playlists = resp.playlists or {}
        state.screen = "playlists"
        set_status("")
    end)
end

local function load_playlist_tracks(playlist_id)
    set_status("Loading playlist...")
    ipc.send({ action = "spotify_playlist_tracks", playlist_id = playlist_id }, function(resp)
        state.tracks = resp.tracks or {}
        state.screen = "results"
        set_status("")
    end)
end

local function play_track(track)
    if not track.bpm then
        set_status("BPM unavailable for this track.")
        return
    end

    -- open in streaming app
    if state.service == "Spotify" and track.uri then
        ipc.send({ action = "spotify_play", uri = track.uri }, function() end)
    end

    -- inject BPM into the game's song config
    -- Dead as Disco stores the active song config in a UObject accessible via UE4SS
    local ok = pcall(function()
        local mgr = UEHelpers.GetMusicManager()
        if mgr then
            mgr.CurrentBPM = track.bpm
            mgr.SongName    = track.name .. " - " .. track.artist
        end
    end)

    set_status(ok
        and string.format("Now playing: %s — BPM set to %d", track.name, track.bpm)
        or  string.format("BPM %d copied — paste it in the BPM field.", track.bpm))

    -- fallback: write to clipboard so user can paste manually
    UEHelpers.SetClipboardText(tostring(track.bpm))

    M.hide()
end

-- ── ImGui UI ─────────────────────────────────────────────────────────────────

function M.draw()
    if not state.visible then return end

    ImGui.SetNextWindowSize(520, 460, ImGuiCond.FirstUseEver)
    ImGui.SetNextWindowPos(200, 150, ImGuiCond.FirstUseEver)

    local open = ImGui.Begin("DiscoFlow — Use Your Music", true,
        ImGuiWindowFlags.NoResize | ImGuiWindowFlags.NoScrollbar)

    if not open then
        M.hide()
        ImGui.End()
        return
    end

    -- ── top bar ──
    if state.screen ~= "services" then
        if ImGui.Button("← Back") then
            state.screen = "services"
            state.tracks = {}
            state.playlists = {}
        end
        ImGui.SameLine()
    end
    ImGui.Text("Service: " .. (state.service or "—"))
    ImGui.Separator()

    -- ── screens ──
    if state.screen == "services" then
        M.draw_services()
    elseif state.screen == "search" then
        M.draw_search()
    elseif state.screen == "results" then
        M.draw_results()
    elseif state.screen == "playlists" then
        M.draw_playlists()
    end

    -- ── status bar ──
    if state.status_msg ~= "" then
        ImGui.Separator()
        ImGui.TextDisabled(state.status_msg)
    end

    ImGui.End()
end

function M.draw_services()
    ImGui.Text("Select a streaming service:")
    ImGui.Spacing()

    if #state.services == 0 then
        ImGui.TextDisabled("No streaming apps detected.")
        ImGui.TextDisabled("Install Spotify, Apple Music, Tidal, or Deezer.")
        ImGui.Spacing()
    end

    for _, svc in ipairs(state.services) do
        local label = svc.name
        if not svc.running and svc.name ~= "Local Files" then
            label = label .. " (not running)"
        end
        if ImGui.Button(label, 480, 36) then
            state.service = svc.name
            state.screen = "search"
        end
    end
end

function M.draw_search()
    ImGui.Text("Search a song or browse playlists:")
    ImGui.Spacing()

    local changed, new_query = ImGui.InputText("##query", state.query, 256)
    if changed then state.query = new_query end
    ImGui.SameLine()
    if ImGui.Button("Search") then search(state.query) end

    if state.service == "Spotify" then
        ImGui.Spacing()
        if ImGui.Button("My Playlists", 480, 32) then load_playlists() end
    end
end

function M.draw_results()
    ImGui.Text(string.format("%d results", #state.tracks))
    ImGui.Separator()

    for _, t in ipairs(state.tracks) do
        local bpm_label = t.bpm and string.format(" [%d BPM]", t.bpm) or " [BPM ?]"
        local duration  = t.duration or ""
        local label     = string.format("%s — %s  %s  %s", t.name, t.artist, duration, bpm_label)

        if ImGui.Button("▶  " .. label, 480, 28) then
            play_track(t)
        end
    end
end

function M.draw_playlists()
    ImGui.Text("Your Spotify Playlists:")
    ImGui.Separator()

    for _, p in ipairs(state.playlists) do
        local label = string.format("%s  (%d tracks)", p.name, p.tracks)
        if ImGui.Button(label, 480, 28) then
            load_playlist_tracks(p.id)
        end
    end
end

-- ── public ───────────────────────────────────────────────────────────────────

function M.show()
    state.visible = true
    if #state.services == 0 then load_services() end
end

function M.hide()
    state.visible = false
end

function M.toggle()
    if state.visible then M.hide() else M.show() end
end

return M
