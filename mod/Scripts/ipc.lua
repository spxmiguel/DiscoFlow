local M = {}

local BASE = os.getenv("LOCALAPPDATA") .. "\\DiscoFlow\\"
local REQUEST_FILE  = BASE .. "request.json"
local RESPONSE_FILE = BASE .. "response.json"

local function write_json(path, data)
    local f = io.open(path, "w")
    if not f then return false end
    f:write(data)
    f:close()
    return true
end

local function read_json(path)
    local f = io.open(path, "r")
    if not f then return nil end
    local content = f:read("*a")
    f:close()
    return content
end

function M.send(request_table, callback)
    local json_str = M.encode(request_table)
    write_json(REQUEST_FILE, json_str)

    -- poll for response (max 5 seconds)
    local deadline = os.clock() + 5
    while os.clock() < deadline do
        local raw = read_json(RESPONSE_FILE)
        if raw then
            os.remove(RESPONSE_FILE)
            local ok, result = pcall(M.decode, raw)
            if ok and callback then callback(result) end
            return
        end
    end
end

function M.read_state()
    local raw = read_json(BASE .. "state.json")
    if not raw then return nil end
    local ok, data = pcall(M.decode, raw)
    return ok and data or nil
end

-- minimal JSON encode/decode (numbers, strings, arrays, objects, booleans)
function M.encode(val)
    local t = type(val)
    if t == "nil" then return "null"
    elseif t == "boolean" then return tostring(val)
    elseif t == "number" then return tostring(val)
    elseif t == "string" then
        return '"' .. val:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', '\\n') .. '"'
    elseif t == "table" then
        -- check if array
        local is_array = #val > 0
        if is_array then
            local parts = {}
            for _, v in ipairs(val) do parts[#parts+1] = M.encode(v) end
            return "[" .. table.concat(parts, ",") .. "]"
        else
            local parts = {}
            for k, v in pairs(val) do
                parts[#parts+1] = M.encode(tostring(k)) .. ":" .. M.encode(v)
            end
            return "{" .. table.concat(parts, ",") .. "}"
        end
    end
    return "null"
end

-- very small JSON decoder (sufficient for backend responses)
function M.decode(s)
    local pos = 1
    local function skip() while pos <= #s and s:sub(pos,pos):match("%s") do pos=pos+1 end end
    local parse
    local function parse_string()
        pos = pos + 1
        local buf = {}
        while pos <= #s do
            local c = s:sub(pos,pos)
            if c == '"' then pos=pos+1; return table.concat(buf) end
            if c == '\\' then
                pos=pos+1; c=s:sub(pos,pos)
                if c=='n' then buf[#buf+1]='\n'
                elseif c=='t' then buf[#buf+1]='\t'
                else buf[#buf+1]=c end
            else buf[#buf+1]=c end
            pos=pos+1
        end
    end
    local function parse_number()
        local n, np = s:match("^(-?%d+%.?%d*[eE]?[+-]?%d*)()", pos)
        pos = np; return tonumber(n)
    end
    local function parse_array()
        pos=pos+1; local arr={}; skip()
        if s:sub(pos,pos)==']' then pos=pos+1; return arr end
        while true do
            arr[#arr+1]=parse(); skip()
            local c=s:sub(pos,pos); pos=pos+1
            if c==']' then return arr end
        end
    end
    local function parse_object()
        pos=pos+1; local obj={}; skip()
        if s:sub(pos,pos)=='}' then pos=pos+1; return obj end
        while true do
            skip(); local k=parse_string(); skip(); pos=pos+1
            obj[k]=parse(); skip()
            local c=s:sub(pos,pos); pos=pos+1
            if c=='}' then return obj end
        end
    end
    parse = function()
        skip()
        local c = s:sub(pos,pos)
        if c=='"' then return parse_string()
        elseif c=='{' then return parse_object()
        elseif c=='[' then return parse_array()
        elseif c=='t' then pos=pos+4; return true
        elseif c=='f' then pos=pos+5; return false
        elseif c=='n' then pos=pos+4; return nil
        else return parse_number() end
    end
    return parse()
end

return M
