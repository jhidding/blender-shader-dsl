let entangled = https://raw.githubusercontent.com/entangled/entangled/v1.2.2/data/config-schema.dhall
                sha256:9bb4c5649869175ad0b662d292fd81a3d5d9ccb503b1c7e316d531b7856fb096

let syntax : entangled.Syntax =
    { matchCodeStart       = "^[ ]*```[[:alpha:]]+"
    , matchCodeEnd         = "^[ ]*```"
    , extractLanguage      = "```([[:alpha:]]+)"
    , extractReferenceName = "```[[:alpha:]]+[ ]+.*id=\"([^\"]*)\".*"
    , extractFileName      = "```[[:alpha:]]+[ ]+.*file=\"([^\"]*)\".*"
    }

let database = Some ".entangled/db.sqlite"

let watchList = [ "docs/python_dsl.md", "docs/about.md" ]

in { entangled = entangled.Config :: { database = database
                                     , watchList = watchList
                                     , syntax = syntax }

   , jupyter = { language = "Python", kernel = "python3" }
   }

