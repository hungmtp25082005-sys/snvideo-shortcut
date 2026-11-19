import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MAIN = (SRC / "SNVideo.cherri").read_text(encoding="utf-8")
CONFIG = (SRC / "config.cherri").read_text(encoding="utf-8")
TIKWM = (SRC / "lib" / "tikwm.cherri").read_text(encoding="utf-8")
SLIDESHOW = (SRC / "lib" / "slideshow.cherri").read_text(encoding="utf-8")
VIDEO = (SRC / "lib" / "video.cherri").read_text(encoding="utf-8")
UPDATE = (SRC / "lib" / "update.cherri").read_text(encoding="utf-8")
COBALT = (SRC / "lib" / "cobalt.cherri").read_text(encoding="utf-8")
ALL_SOURCE = "\n".join(
    path.read_text(encoding="utf-8") for path in sorted(SRC.rglob("*.cherri"))
)


class SourceContractTests(unittest.TestCase):
    def test_main_declares_share_sheet_inputs(self):
        self.assertIn("#define inputs url, text", MAIN)
        self.assertIn("#define from sharesheet", MAIN)
        self.assertNotIn("#define noinput getclipboard", MAIN)

    def test_required_cherri_action_categories_are_included(self):
        required = (
            "actions/web",
            "actions/text",
            "actions/sharing",
            "actions/documents",
            "actions/photos",
        )
        for category in required:
            self.assertIn(f"#include '{category}'", MAIN)

    def test_clipboard_is_only_read_after_explicit_menu_choice(self):
        menu_position = MAIN.index('item "Dùng liên kết trong Clipboard"')
        clipboard_position = MAIN.index("getClipboard()")
        self.assertLess(menu_position, clipboard_position)

    def test_error_paths_stop_in_the_current_caller(self):
        self.assertNotIn("stopWithError(", ALL_SOURCE)

    def test_audio_stays_disabled_until_gate_b(self):
        self.assertRegex(CONFIG, r"const ENABLE_AUDIO\s*=\s*false")
        self.assertIn('@audioEnabled == true && @audioValid == "1"', VIDEO)
        self.assertIn('@audioEnabled == true && @audioValid == "1"', SLIDESHOW)

    def test_cobalt_message_precedes_browser_handoff(self):
        self.assertLess(COBALT.index("alert("), COBALT.index("openURL(COBALT_URL)"))

    def test_router_uses_parsed_hostname_before_tikwm(self):
        host_position = MAIN.index('getURLDetail(@cleanURL, "Host")')
        route_position = MAIN.index('endsWith ".tiktok.com"')
        tikwm_position = MAIN.index("processTikTok(@cleanURL)")
        self.assertLess(host_position, route_position)
        self.assertLess(route_position, tikwm_position)
        self.assertIn('@urlHost == "tiktok.com"', MAIN)

    def test_tikwm_endpoint_and_single_encoding_stage(self):
        self.assertIn(
            'const TIKWM_ENDPOINT = "https://www.tikwm.com/api/"', CONFIG
        )
        self.assertEqual(TIKWM.count("urlEncode("), 1)
        self.assertIn("?url={@encodedURL}&hd=1", TIKWM)
        self.assertNotIn("expandURL(", ALL_SOURCE)

    def test_slideshow_is_sequential_without_fixed_delay(self):
        loop_position = SLIDESHOW.index("for imageItem in @images")
        download_position = SLIDESHOW.index("downloadURL(@imageURL)")
        save_position = SLIDESHOW.index("savePhoto(@imageFile")
        self.assertLess(loop_position, download_position)
        self.assertLess(download_position, save_position)
        self.assertNotIn("wait(", SLIDESHOW)

    def test_update_flow_is_disabled_until_configured_and_allowlisted(self):
        self.assertRegex(CONFIG, r'const MANIFEST_URL\s*=\s*""')
        self.assertIn('@manifestHost != "raw.githubusercontent.com"', UPDATE)
        self.assertIn('@updateHost != "www.icloud.com"', UPDATE)

    def test_manifest_example_matches_build_contract(self):
        manifest = json.loads((ROOT / "manifest.example.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 1)
        self.assertIsInstance(manifest["build"], int)
        self.assertGreater(manifest["build"], 0)
        self.assertEqual(manifest["minimum_ios"], "TBD")
        self.assertTrue(manifest["shortcut_icloud_url"].startswith("https://www.icloud.com/shortcuts/"))

    def test_no_obvious_secret_material(self):
        secret_patterns = (
            r"ghp_[A-Za-z0-9]{20,}",
            r"github_pat_[A-Za-z0-9_]{20,}",
            r"Bearer\s+[A-Za-z0-9._-]{20,}",
        )
        for pattern in secret_patterns:
            self.assertIsNone(re.search(pattern, ALL_SOURCE, re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()
