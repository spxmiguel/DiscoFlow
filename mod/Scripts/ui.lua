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

local function fmt_duration(ms)
    if not ms or ms == 0 then return "" end
    local s = math.floor(ms / 1000)
    return string.format("%d:%02d", math.floor(s / 60), s % 60)
end

local function clamp_bpm(bpm)
    if not bpm or bpm <= 0 then return nil end
    while bpm < 80  do bpm = bpm * 2 end
    while bpm > 200 do bpm = bpm / 2 end
    return math.floor(bpm)
end

local function has_library()
    local lib = ipc.read_library()
    return lib and lib.tracks and #lib.tracks > 0
end

local function load_library()
    local lib = ipc.read_library()
    if not lib or not lib.tracks or #lib.tracks == 0 then
        set_status("Biblioteca vazia — abra o app DiscoFlow para adicionar músicas.")
        return
    end
    state.tracks = {}
    for _, t in ipairs(lib.tracks) do
        state.tracks[#state.tracks + 1] = {
            name     = t.title  or "Desconhecido",
            artist   = t.artist or "Desconhecido",
            bpm      = clamp_bpm(t.bpm),
            duration = fmt_duration(t.duration_ms),
            path     = t.path,
            source   = "local",
        }
    end
    state.screen = "results"
    set_status(string.format("%d faixas na biblioteca", #state.tracks))
end

local function load_services()
    set_status("Detectando apps de streaming...")
    ipc.send({ action = "detect" }, function(resp)
        state.services = resp.services or {}
        state.screen = "services"
        set_status("")
    end)
end

local SEARCH_ACTIONS = {
    ["Spotify"]       = "spotify_search",
    ["Deezer"]        = "deezer_search",
    ["Apple Music"]   = "apple_music_search",
    ["Tidal"]         = "tidal_search",
    ["YouTube Music"] = "youtube_music_search",
    ["Amazon Music"]  = "amazon_music_search",
}

local PLAYLIST_ACTIONS = {
    ["Spotify"] = { list = "spotify_playlists",       tracks = "spotify_playlist_tracks" },
    ["Tidal"]   = { list = "tidal_playlists",         tracks = "tidal_playlist_tracks"   },
}

local function search(query)
    if not state.service or query == "" then return end
    local action = SEARCH_ACTIONS[state.service]
    if not action then
        set_status("Servico nao suportado: " .. state.service)
        return
    end
    set_status("Pesquisando...")
    ipc.send({ action = action, query = query }, function(resp)
        if resp.error then
            set_status("Erro: " .. resp.error)
            return
        end
        state.tracks = resp.tracks or {}
        state.screen = "results"
        set_status(#state.tracks == 0 and "Nenhum resultado." or "")
    end)
end

local function load_playlists()
    local pa = PLAYLIST_ACTIONS[state.service]
    if not pa then return end
    set_status("Carregando playlists...")
    ipc.send({ action = pa.list }, function(resp)
        state.playlists = resp.playlists or {}
        state.screen = "playlists"
        set_status("")
    end)
end

local function load_playlist_tracks(playlist_id)
    local pa = PLAYLIST_ACTIONS[state.service]
    if not pa then return end
    set_status("Carregando playlist...")
    ipc.send({ action = pa.tracks, playlist_id = playlist_id }, function(resp)
        state.tracks = resp.tracks or {}
        state.screen = "results"
        set_status("")
    end)
end

local function do_play_track(track)
    -- open in streaming app (Spotify only for now)
    if track.source ~= "local" then
        if state.service == "Spotify" and track.uri then
            ipc.send({ action = "spotify_play", uri = track.uri }, function() end)
        end
    end

    -- inject BPM into game
    local ok = pcall(function()
        local mgr = UEHelpers.GetMusicManager()
        if mgr then
            mgr.CurrentBPM = track.bpm
            mgr.SongName    = track.name .. " - " .. track.artist
        end
    end)

    set_status(ok
        and string.format("Tocando: %s — BPM definido para %d", track.name, track.bpm)
        or  string.format("BPM %d copiado — cole no campo BPM.", track.bpm))

    UEHelpers.SetClipboardText(tostring(track.bpm))
    M.hide()
end

local function play_track(track)
    -- BPM-on-demand: detect via iTunes preview before playing
    if not track.bpm then
        if track.source == "local" then
            set_status("BPM nao disponivel para esta faixa.")
            return
        end
        set_status("Detectando BPM... (alguns segundos)")
        ipc.send_long(
            { action = "bpm_from_preview",
              url    = track.preview_url or "",
              artist = track.artist or "",
              name   = track.name   or "" },
            function(resp)
                if resp and resp.bpm and resp.bpm > 0 then
                    track.bpm = resp.bpm
                    do_play_track(track)
                else
                    set_status("Nao foi possivel detectar o BPM desta faixa.")
                end
            end,
            25
        )
        return
    end

    do_play_track(track)
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
    ImGui.Text("Selecione a fonte de música:")
    ImGui.Spacing()

    -- Minha Biblioteca (local, always shown)
    if has_library() then
        if ImGui.Button("Minha Biblioteca  (app DiscoFlow)", 480, 36) then
            state.service = "Minha Biblioteca"
            load_library()
        end
        ImGui.Spacing()
    else
        ImGui.TextDisabled("App DiscoFlow nao instalado — biblioteca vazia.")
        ImGui.Spacing()
    end

    -- streaming services (require backend)
    if #state.services == 0 then
        ImGui.TextDisabled("Nenhum app de streaming detectado.")
        ImGui.TextDisabled("Instale Spotify ou Deezer, ou use a Biblioteca Manual.")
        ImGui.Spacing()
    end
    for _, svc in ipairs(state.services) do
        local label = svc.name
        if not svc.running and svc.name ~= "Local Files" then
            label = label .. " (nao iniciado)"
        end
        if ImGui.Button(label, 480, 36) then
            state.service = svc.name
            state.screen = "search"
        end
    end
end

function M.draw_search()
    ImGui.Text("Buscar musica:")
    ImGui.Spacing()

    local changed, new_query = ImGui.InputText("##query", state.query, 256)
    if changed then state.query = new_query end
    ImGui.SameLine()
    if ImGui.Button("Buscar") then search(state.query) end

    if PLAYLIST_ACTIONS[state.service] then
        ImGui.Spacing()
        if ImGui.Button("Minhas Playlists", 480, 32) then load_playlists() end
    end
end

function M.draw_results()
    ImGui.Text(string.format("%d resultado(s)", #state.tracks))
    ImGui.Separator()

    for _, t in ipairs(state.tracks) do
        local bpm_label = t.bpm and string.format(" [%d BPM]", t.bpm) or " [BPM?]"
        local duration  = t.duration or ""
        local label     = string.format("%s — %s  %s  %s", t.name, t.artist, duration, bpm_label)

        if ImGui.Button("▶  " .. label, 480, 28) then
            play_track(t)
        end
    end
end

function M.draw_playlists()
    ImGui.Text(string.format("Playlists — %s:", state.service or ""))
    ImGui.Separator()

    for _, p in ipairs(state.playlists) do
        local label = string.format("%s  (%d faixas)", p.name, p.tracks or 0)
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
