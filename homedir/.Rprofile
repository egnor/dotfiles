.maybe_message <- if (interactive()) message else function(...) invisible()
if (!isNamespaceLoaded("renv") && file.exists("renv/activate.R")) {
  .maybe_message("🌱 ~/.Rprofile: activating `renv`")
  source("renv/activate.R")
  renv::restore()

  .maybe_message()
  .maybe_message("😋 ~/.Rprofile: loading local code (devtools::load_all())")
  options(keep.source = TRUE)
  devtools::load_all()
}

invisible()
