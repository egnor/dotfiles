if (!isNamespaceLoaded("renv") && file.exists("renv/activate.R")) {
  message("🌱 ~/.Rprofile: activating `renv`")
  source("renv/activate.R")

  message()
  message("😋 ~/.Rprofile: loading local code (devtools::load_all())")
  library(datasets)
  devtools::load_all()
}

invisible()
