-- Let Neovim's built-in vim/vimdoc parsers handle those filetypes instead of
-- nvim-treesitter's own copies.
--
-- On nvim-treesitter's `main` branch, parsers (.so, recompiled asynchronously
-- by :TSUpdate) and queries (.scm, updated the instant the plugin updates) are
-- versioned separately and can drift apart after an update -- producing
-- "Query error ... Invalid node type" failures. The most visible one is on the
-- `:` command line, which Noice highlights as filetype=vim.
--
-- Neovim ships the vim/vimdoc parsers and their queries together in the same
-- release, so that pair can never drift. Dropping them from ensure_installed
-- (and uninstalling the shadowing copies under ~/.local/share/nvim/site/) makes
-- Neovim fall back to its own matched built-ins. Other languages stay managed by
-- nvim-treesitter for its richer queries.
return {
  {
    "nvim-treesitter/nvim-treesitter",
    opts = function(_, opts)
      local drop = { vim = true, vimdoc = true }
      opts.ensure_installed = vim.tbl_filter(function(lang)
        return not drop[lang]
      end, opts.ensure_installed or {})
    end,
  },
}
