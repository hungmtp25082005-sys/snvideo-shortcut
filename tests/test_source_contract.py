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
WORKFLOW = (ROOT / ".github" / "workflows" / "build-shortcut.yml").read_text(encoding="utf-8")
INSTALLER = (ROOT / "scripts" / "install-cherri.sh").read_text(encoding="utf-8")
VERIFY_SHORTCUT = (ROOT / "scripts" / "verify_shortcut.py").read_text(encoding="utf-8")
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

    def test_shortcut_input_is_checked_before_text_conversion(self):
        input_check_position = MAIN.index("if ShortcutInput")
        input_assignment_position = MAIN.index('@inputText = "{ShortcutInput}"')
        self.assertLess(input_check_position, input_assignment_position)
        self.assertNotIn('@inputText = "{ShortcutInput}"', MAIN[:input_check_position])

    def test_clipboard_is_only_read_after_explicit_menu_choice(self):
        menu_position = MAIN.index('item "Dùng liên kết trong Clipboard"')
        clipboard_position = MAIN.index("getClipboard()")
        self.assertLess(menu_position, clipboard_position)

    def test_error_paths_stop_in_the_current_caller(self):
        self.assertNotIn("stopWithError(", ALL_SOURCE)

    def test_audio_stays_disabled_until_gate_b(self):
        self.assertRegex(CONFIG, r"const ENABLE_AUDIO\s*=\s*false")
        self.assertIn("@audioEnabled == true && @audioValid == true", VIDEO)
        self.assertIn("@audioEnabled == true && @audioValid == true", SLIDESHOW)

    def test_cobalt_message_precedes_browser_handoff(self):
        self.assertLess(COBALT.index("alert("), COBALT.index("openURL(COBALT_URL)"))

    def test_router_uses_parsed_hostname_before_tikwm(self):
        host_position = MAIN.index('getURLDetail(@cleanURL, "Host")')
        route_position = MAIN.index('endsWith ".tiktok.com"')
        tikwm_position = MAIN.index("#include 'lib/tikwm.cherri'")
        self.assertLess(host_position, route_position)
        self.assertLess(route_position, tikwm_position)
        self.assertIn('@urlHost == "tiktok.com"', MAIN)

    def test_tikwm_short_links_expand_before_single_encoding_stage(self):
        self.assertIn(
            'const TIKWM_ENDPOINT = "https://www.tikwm.com/api/"', CONFIG
        )
        expand_position = TIKWM.index("expandURL(@cleanURL)")
        encode_position = TIKWM.index("urlEncode(@requestURL)")
        self.assertLess(expand_position, encode_position)
        self.assertEqual(TIKWM.count("expandURL("), 1)
        self.assertEqual(TIKWM.count("urlEncode("), 1)
        self.assertIn('@urlHost == "vt.tiktok.com"', TIKWM)
        self.assertIn('@urlHost == "vm.tiktok.com"', TIKWM)
        self.assertIn('@expandedScheme != "https"', TIKWM)
        self.assertIn("?url={@encodedURL}&hd=1", TIKWM)

    def test_tikwm_soft_errors_include_typed_code_and_message(self):
        self.assertIn('@responseCodeValue = getValue(@response, "code")', TIKWM)
        self.assertIn("@responseCode = number(@responseCodeValue)", TIKWM)
        self.assertIn('@responseMsgValue = getValue(@response, "msg")', TIKWM)
        self.assertIn("@responseMsg = getText(@responseMsgValue)", TIKWM)
        self.assertIn("if @responseCode != 0", TIKWM)
        self.assertIn(
            'alert("TikWM lỗi (code {@responseCode}): {@responseMsg}", "SNVideo")',
            TIKWM,
        )

    def test_constant_dictionary_keys_use_get_value_actions(self):
        self.assertIsNone(re.search(r"@[A-Za-z0-9_]+\['[^']+'\]", ALL_SOURCE))

    def test_slideshow_selects_labels_then_saves_sequentially(self):
        choice_position = SLIDESHOW.index("chooseFromList(imageLabels")
        loop_position = SLIDESHOW.index("for imageItem in @images")
        download_position = SLIDESHOW.index("downloadURL(@imageURL)")
        save_position = SLIDESHOW.index("savePhoto(@imageFile")
        self.assertLess(choice_position, loop_position)
        self.assertLess(loop_position, download_position)
        self.assertLess(download_position, save_position)
        self.assertIn('"Image0{@labelIndex}"', SLIDESHOW)
        self.assertIn('"Image0{@imageIndex}"', SLIDESHOW)
        self.assertIn(
            'chooseFromList(imageLabels, "Chọn ảnh cần tải", true, true)',
            SLIDESHOW,
        )
        self.assertIn("@selectedLabelSet contains @imageSelectionToken", SLIDESHOW)
        self.assertNotIn("quicklook(", SLIDESHOW)
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

    def test_source_has_no_cherri_functions_or_self_invocation_dispatcher(self):
        self.assertIsNone(re.search(r"(?m)^\s*function\s+", ALL_SOURCE))
        self.assertNotIn("runSelf(", ALL_SOURCE)
        self.assertNotIn("cherri_functions", ALL_SOURCE)

    def test_variables_are_not_declared_without_initial_values(self):
        uninitialized = r"(?m)^\s*@[A-Za-z0-9_]+\s*:\s*(array|dictionary|text|number|bool)\s*$"
        self.assertIsNone(re.search(uninitialized, ALL_SOURCE))

    def test_flat_modules_are_included_once_in_the_main_pipeline(self):
        expected_includes = (
            "lib/update.cherri",
            "lib/common.cherri",
            "lib/tikwm.cherri",
            "lib/cobalt.cherri",
        )
        for include in expected_includes:
            self.assertEqual(MAIN.count(f"#include '{include}'"), 1)

    def test_workflow_uses_cherri_240_cli_output_contract(self):
        self.assertNotIn("--share anyone", WORKFLOW)
        self.assertNotIn("--output ", WORKFLOW)
        self.assertIn("--share=anyone", WORKFLOW)
        self.assertIn("--output=dist/SNVideo.shortcut", WORKFLOW)
        self.assertIn(
            "mv src/SNVideo_unsigned.shortcut build/SNVideo.unsigned.shortcut",
            WORKFLOW,
        )
        self.assertIn(
            "python3 scripts/verify_shortcut.py build/SNVideo.unsigned.shortcut",
            WORKFLOW,
        )

    def test_compiled_shortcut_verifier_rejects_invalid_actions(self):
        self.assertIn('endswith(".runworkflow")', VERIFY_SHORTCUT)
        self.assertIn('== "cherri_functions"', VERIFY_SHORTCUT)
        self.assertIn('endswith(".setvariable")', VERIFY_SHORTCUT)
        self.assertIn('"WFInput" not in parameters', VERIFY_SHORTCUT)

    def test_cherri_installer_builds_the_pinned_tag_for_both_jobs(self):
        pinned_commit = "2afd41f96988ca4a20aa0afcbf763251e4b20fb7"
        broken_install = "go install " + "github.com/electrikmilk/cherri"
        self.assertNotIn(broken_install, WORKFLOW)
        self.assertEqual(
            WORKFLOW.count('bash scripts/install-cherri.sh "${CHERRI_VERSION}"'),
            2,
        )
        self.assertIn(f"CHERRI_COMMIT: {pinned_commit}", WORKFLOW)
        self.assertIn(f'DEFAULT_COMMIT="{pinned_commit}"', INSTALLER)
        self.assertIn('git -c core.autocrlf=false clone \\\n', INSTALLER)
        self.assertIn('go build -C "$source_dir"', INSTALLER)

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
