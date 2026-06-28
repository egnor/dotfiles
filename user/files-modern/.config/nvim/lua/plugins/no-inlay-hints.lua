-- Disable injection of type hints
return {
  { "neovim/nvim-lspconfig", opts = { inlay_hints = { enabled = false } } },
}
