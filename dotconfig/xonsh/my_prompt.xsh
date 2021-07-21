def set_prompt():
    from xonsh.procs.pipelines import CommandPipeline as CP

    hostname = $PROMPT_FIELDS["hostname"]

    def make_right_prompt():
        ret_code = $PROMPT_FIELDS["ret_code"]()
        env_name = $PROMPT_FIELDS["env_name"]()
        branch_color = $PROMPT_FIELDS["branch_color"]()
        curr_branch = $PROMPT_FIELDS["curr_branch"]()
        cwd = $PROMPT_FIELDS["cwd"]()

        return (
            f" " +
            (f"{{BACKGROUND_RED}}{ret_code}{{RESET}} " if ret_code else "") +
            (f"{{FAINT_CYAN}}{env_name}" if env_name else "") +
            (f"{branch_color}{curr_branch} " if curr_branch else "") +
            f"{{WHITE}}{cwd} {{BOLD_INTENSE_WHITE}}{hostname} "
        )

    $PROMPT = ": "

    $RIGHT_PROMPT = make_right_prompt

    $TITLE = "{current_job:{} | }{cwd} {hostname}"  # Doesn't support functions

set_prompt()
del set_prompt  # keep namespace clean
