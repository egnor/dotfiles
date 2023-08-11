if (!isNamespaceLoaded("renv") && file.exists("renv/activate.R")) {
  message("🌱 ~/.Rprofile: activating `renv`")
  source("renv/activate.R")
  renv::restore()

  message()
  message("😋 ~/.Rprofile: loading local code (devtools::load_all())")
  library(datasets)  # Needed for some strange reason??
  options(keep.source = TRUE)
  devtools::load_all()
}

invisible()
