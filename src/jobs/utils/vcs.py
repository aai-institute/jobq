import subprocess


def get_git_user_info():
    try:
        name = subprocess.check_output(
            ["git", "config", "user.name"], encoding="utf-8"
        ).strip()
        email = subprocess.check_output(
            ["git", "config", "user.email"], encoding="utf-8"
        ).strip()
        return f"{name} <{email}>"
    except subprocess.CalledProcessError:
        return None


def get_git_last_committer_info():
    try:
        return subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%an <%ae>"], encoding="utf-8"
        ).strip()
    except subprocess.CalledProcessError:
        return None
