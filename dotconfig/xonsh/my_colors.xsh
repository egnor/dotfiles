def set_colors():
    import xonsh.tools
    from pygments.token import Token 

    regular = "nobold noitalic #FFF bg:"
    comment = "bold noitalic #FF0 bg:"
    error = "bold noitalic #F77 bg:"  # Not actually used?
    name = "bold noitalic #DDD bg:"
    name_builtin = "bold noitalic #7D7 bg:"
    literal = "bold noitalic #ADF bg:"
    literal_escape = "bold noitalic #DEF bg:"
    noise = "nobold noitalic #BBB bg:"
    suggest = "nobold noitalic #999 bg:"
    menu = "nobold noitalic #000 bg:#BBB"
    menu_selected = "nobold noitalic #FFF bg:#007"
    menu_scroll = "nobold noitalic #000 bg:#777"

    $XONSH_STYLE_OVERRIDES.update({
        Token: regular,
        Token.Comment: comment,
        Token.Comment.Hashbang: comment,
        Token.Comment.Multiline: comment,
        Token.Comment.Preproc: comment,
        Token.Comment.PreprocFile: comment,
        Token.Comment.Single: comment,
        Token.Comment.Special: comment,
        Token.Error: error,
        Token.Escape: regular,
        Token.Generic: regular,
        Token.Generic.Deleted: regular,
        Token.Generic.Emph: regular,
        Token.Generic.Error: error,
        Token.Generic.Heading: regular,
        Token.Generic.Inserted: regular,
        Token.Generic.Output: regular,
        Token.Generic.Prompt: regular,
        Token.Generic.Strong: regular,
        Token.Generic.Subheading: regular,
        Token.Generic.Traceback: regular,
        Token.Keyword: noise,
        Token.Keyword.Constant: noise,
        Token.Keyword.Declaration: noise,
        Token.Keyword.Namespace: noise,
        Token.Keyword.Pseudo: noise,
        Token.Keyword.Reserved: noise,
        Token.Keyword.Type: noise,
        Token.Literal: literal,
        Token.Literal.Number: literal,
        Token.Literal.String: literal,
        Token.Literal.String.Doc: literal,
        Token.Literal.String.Escape: literal_escape,
        Token.Literal.String.Interpol: literal,
        Token.Literal.String.Other: literal,
        Token.Literal.String.Regex: literal,
        Token.Literal.String.Symbol: literal,
        Token.Name: name,
        Token.Name.Attribute: name,
        Token.Name.Builtin: name_builtin,  # Python builtins & shell commands
        Token.Name.Class: name,
        Token.Name.Constant: name,
        Token.Name.Decorator: name,
        Token.Name.Exception: name,
        Token.Name.Entity: name,
        Token.Name.Function: name,
        Token.Name.Label: name,
        Token.Name.Namespace: name,
        Token.Name.Other: name,
        Token.Name.Tag: name,
        Token.Name.Variable: name,
        Token.Operator: noise,
        Token.Operator.Word: noise,
        Token.Other: regular,
        Token.PTK.Aborting: error,
        Token.PTK.AutoSuggestion: suggest,
        Token.PTK.CompletionMenu: menu_scroll,
        Token.PTK.CompletionMenu.Completion: menu,
        Token.PTK.CompletionMenu.Completion.Current: menu_selected,
        Token.PTK.Scrollbar.Arrow: menu_scroll,
        Token.PTK.Scrollbar.Background: menu_scroll,
        Token.PTK.Scrollbar.Button: menu_scroll,
        Token.Punctuation: noise,
        Token.Text: regular,
        Token.Text.Whitespace: regular,
    })

    # Used for ls and also for command line highlighting within xonsh
    normal = "RESET",
    special = "BOLD_YELLOW",
    program = "BOLD_#7D7",
    directory = "BOLD_#ADF",
    symlink = "BOLD_#DEF",
    missing = "BOLD_BLACK", "BACKGROUND_WHITE",
    red_alert = "BOLD_WHITE", "BACKGROUND_RED",
    yellow_alert = "BOLD_BLACK", "BACKGROUND_YELLOW",
    $LS_COLORS = {
        "bd": special,       # Block Device
        "ca": yellow_alert,  # CApability
        "cd": special,       # Char Device
        "di": directory,     # DIrectory
        "do": special,       # DOor
        "ex": program,       # EXecutable
        "fi": normal,        # regular FIle
        "ln": symlink,       # symLiNk
        "mh": special,       # Multiply Hardlinked file
        "mi": missing,       # MIssing link target
        "or": missing,       # ORphan symlink
        "ow": yellow_alert,  # Other-Writable
        "pi": special,       # named PIpe
        "rs": normal,        # color ReSet
        "sg": yellow_alert,  # SetGid
        "so": special,       # SOcket
        "st": directory,     # STicky, not other-writable
        "su": red_alert,     # SetUid
        "tw": yellow_alert,  # sTicky and other-Writable
    }

set_colors()
del set_colors  # keep namespace clean
