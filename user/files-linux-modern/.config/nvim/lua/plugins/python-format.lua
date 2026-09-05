-- Use ruff for Python formatting (instead of black), but only in projects
-- with evidence that ruff is actually configured -- editing a file in some
-- random repo shouldn't produce unsolicited whole-file reformatting on save.
local function has_ruff_config(dir)
  for _, name in ipairs({ "ruff.toml", ".ruff.toml" }) do
    if vim.fs.find(name, { path = dir, upward = true })[1] then
      return true
    end
  end
  local pyprojects =
    vim.fs.find("pyproject.toml", { path = dir, upward = true, limit = math.huge })
  for _, pyproject in ipairs(pyprojects) do
    for _, line in ipairs(vim.fn.readfile(pyproject)) do
      if line:find("[tool.ruff", 1, true) then
        return true
      end
    end
  end
  return false
end

return {
  {
    "stevearc/conform.nvim",
    opts = {
      formatters_by_ft = {
        python = { "ruff_format" },
      },
      formatters = {
        ruff_format = {
          condition = function(_, ctx)
            return has_ruff_config(ctx.dirname)
          end,
        },
      },
    },
  },
  {
    -- When the condition above declines, LazyVim falls back to LSP
    -- formatting, and the ruff language server (lang.python extra) would
    -- reformat anyway -- so strip its formatting capability; conform above
    -- is the only path to ruff formatting.
    "neovim/nvim-lspconfig",
    opts = {
      setup = {
        ruff = function()
          Snacks.util.lsp.on({ name = "ruff" }, function(_, client)
            -- hover disable replicates the lang.python extra's setup.ruff,
            -- which this override replaces (pyright provides hover)
            client.server_capabilities.hoverProvider = false
            client.server_capabilities.documentFormattingProvider = false
            client.server_capabilities.documentRangeFormattingProvider = false
          end)
        end,
      },
    },
  },
}
