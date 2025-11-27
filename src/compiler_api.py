import uuid
import tempfile
import os
import re
import shutil
import time

from parser import parse_text
from renderer import render


INSTANCE_ID = uuid.uuid4().hex

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
THEMES_SRC = os.path.join(BASE_DIR, "themes")

ROOT_TEMP = os.path.join(tempfile.gettempdir(), "ascriptstudio", INSTANCE_ID)

THEMES_DST = os.path.join(ROOT_TEMP, "themes")


def _ensure_temp_environment():
    os.makedirs(ROOT_TEMP, exist_ok=True)

    if not os.path.exists(THEMES_DST):
        print("[aScript] Copying theme folder...")
        shutil.copytree(THEMES_SRC, THEMES_DST)
        print(f"[aScript] Copied theme folder to {THEMES_DST}")
    else:
        pass


def _cleanup_old_previews():
    for filename in os.listdir(ROOT_TEMP):
        if filename == "themes":
            continue

        if filename.startswith("preview_") and filename.endswith(".html"):
            try:
                os.remove(os.path.join(ROOT_TEMP, filename))
            except Exception as e:
                print("[aScript] Warning: Could not delete old preview:", e)


def render_to_tempfile(ascript_text: str) -> str:
    _ensure_temp_environment()

    _cleanup_old_previews()

    file_id = uuid.uuid4().hex
    output_path = os.path.join(ROOT_TEMP, f"preview_{file_id}.html")

    start_time = time.time()

    ast = parse_text(ascript_text)
    html_out = render(ast)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    elapsed = round((time.time() - start_time) * 1000, 2)
    print(f"[aScript] wrote {output_path} in {elapsed}ms")

    return output_path




def cleanup_instance_directory():
    try:
        if os.path.exists(ROOT_TEMP):
            shutil.rmtree(ROOT_TEMP)
            print(f"[aScript] Cleaned instance folder {ROOT_TEMP}")

        top_level = os.path.dirname(ROOT_TEMP)

        if os.path.exists(top_level) and not os.listdir(top_level):
            shutil.rmtree(top_level)
            print(f"[aScript] Removed empty ascriptstudio root folder {top_level}")

    except Exception as e:
        print("[aScript] Warning: Cleanup failed:", e)



def export_standalone_html(ascript_text: str, output_path: str):

    html_path = render_to_tempfile(ascript_text)

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # bit heavier regex because the style tags can be funny
    link_regex = re.compile(
        r"<link\b[^>]*?rel=['\"]stylesheet['\"][^>]*?href=['\"]([^'\"]+)['\"][^>]*?>",
        re.IGNORECASE | re.DOTALL,
    )

    match = link_regex.search(html)

    if not match:
        print("[aScript] No stylesheet link found. Exporting without inline CSS.")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print("[aScript] Standalone export saved to:", output_path)
        return output_path

    css_rel_path = match.group(1)
    css_abs_path = os.path.join(THEMES_DST, css_rel_path.replace("themes/", "", 1))

    if not os.path.exists(css_abs_path):
        print("[aScript] Stylesheet found but missing on disk:", css_abs_path)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path

    with open(css_abs_path, "r", encoding="utf-8") as f:
        css_content = f.read()

    style_tag = "<style>\n" + css_content + "\n</style>"

    html_standalone = link_regex.sub(style_tag, html)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_standalone)

    print("[aScript] Standalone export saved to:", output_path)
    return output_path