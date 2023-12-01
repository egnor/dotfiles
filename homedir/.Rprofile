options(keep.source = TRUE)
.maybe_message <- if (interactive()) message else function(...) invisible()
if (!isNamespaceLoaded("renv") && file.exists("renv/activate.R")) {
  .maybe_message("🌱 ~/.Rprofile: activating `renv`")
  source("renv/activate.R")
  renv::restore()
}

invisible()
