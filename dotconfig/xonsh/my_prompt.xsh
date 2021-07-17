def set_prompt():
    from xonsh.procs.pipelines import CommandPipeline as CP

    def prompt_command_error():
        rv = __builtins__.get("_")
        return rv.returncode if isinstance(rv, CP) and rv.returncode else None

    $PROMPT_FIELDS["command_error"] = prompt_command_error

    $PROMPT = ": "

    $RIGHT_PROMPT = (
        "{BACKGROUND_RED}{command_error: {} }{RESET} "
        "{FAINT_CYAN}{env_name}"
        "{branch_color}{curr_branch:{} }"
        "{WHITE}{cwd} "
        "{BOLD_INTENSE_WHITE}{hostname} "
    )

    $TITLE = "{current_job:{} | }{cwd} {hostname}"

set_prompt()
del set_prompt  # keep namespace clean
