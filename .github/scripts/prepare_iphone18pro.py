#!/usr/bin/env python3
"""Safe, idempotent adaptation of DuarteSantos8/openGym for personal iPhone use.

Applies only narrowly scoped changes. The upstream project supplies the actual application.
GNU AGPL-3.0-or-later applies to modifications of upstream code.
"""
import argparse
import json
import os
from pathlib import Path
import plistlib
import re

CSS_MARKER = '/* BEGIN iPhone18Pro personal tweaks */'
CSS_END = '/* END iPhone18Pro personal tweaks */'
CSS = '''/* BEGIN iPhone18Pro personal tweaks */
/* 402 CSS pt wide on the iPhone 18 Pro at standard display scaling.
   Upstream already handles Dynamic Island and Home Indicator safe areas via
   --sat and --sab; deliberately do not double-add those insets. */
@media (hover: none) and (pointer: coarse) and (max-width: 430px) {
  input:not([type="checkbox"]):not([type="radio"]),
  select, textarea { font-size: max(16px, 1em); }
  button, [role="button"] { -webkit-tap-highlight-color: transparent; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; }
}
/* END iPhone18Pro personal tweaks */'''


def prepare(root: Path, bundle_id: str, app_name: str) -> dict:
    root = root.resolve()
    frontend = root / 'frontend'
    expected = [
        frontend / 'package.json',
        frontend / 'src/index.css',
        frontend / 'capacitor.config.json',
        frontend / 'ios/App/App/Info.plist',
        frontend / 'ios/App/App.xcodeproj/project.pbxproj',
    ]
    missing = [str(p.relative_to(root)) for p in expected if not p.is_file()]
    if missing:
        raise FileNotFoundError('Expected the actual openGym source checkout; missing: ' + ', '.join(missing))
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z][A-Za-z0-9]*){2,}', bundle_id):
        raise ValueError('Bundle ID must be a reverse-domain identifier, e.g. com.example.opengym')

    css_path = frontend / 'src/index.css'
    css = css_path.read_text('utf-8')
    if CSS_MARKER in css:
        css = re.sub(re.escape(CSS_MARKER) + r'.*?' + re.escape(CSS_END), CSS, css, flags=re.S)
    else:
        css = css.rstrip() + '\n\n' + CSS + '\n'
    css_path.write_text(css, encoding='utf-8')

    config_path = frontend / 'capacitor.config.json'
    config = json.loads(config_path.read_text('utf-8'))
    config['appId'] = bundle_id
    config['appName'] = app_name
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    plist_path = frontend / 'ios/App/App/Info.plist'
    with plist_path.open('rb') as f:
        plist = plistlib.load(f)
    plist['CFBundleDisplayName'] = app_name
    plist['NSCameraUsageDescription'] = '仅在扫码或为自定义健身动作拍摄照片与视频时使用摄像头。'
    plist['NSMicrophoneUsageDescription'] = '仅在为自定义健身动作录制带声音的视频时使用麦克风。'
    # A portrait-only phone UI avoids accidental landscape clipping while logging a set.
    plist['UISupportedInterfaceOrientations'] = ['UIInterfaceOrientationPortrait']
    with plist_path.open('wb') as f:
        plistlib.dump(plist, f, fmt=plistlib.FMT_XML, sort_keys=False)

    project_path = frontend / 'ios/App/App.xcodeproj/project.pbxproj'
    project = project_path.read_text('utf-8')
    project, count = re.subn(r'(?m)(PRODUCT_BUNDLE_IDENTIFIER\s*=\s*)([^;]+)(;)',
                             lambda m: f'{m.group(1)}{bundle_id}{m.group(3)}', project)
    if count < 1:
        raise ValueError('No PRODUCT_BUNDLE_IDENTIFIER found; inspect upstream Xcode project before continuing')
    project_path.write_text(project, encoding='utf-8')

    # App localization already ships with zh (Simplified Chinese) in upstream.
    # The app language can be selected in Settings; no fragile state-store edits.
    return {'repository': str(root), 'appId': bundle_id, 'appName': app_name,
            'project_configs_modified': count, 'css_marker_count': css.count(CSS_MARKER)}


def main():
    ap = argparse.ArgumentParser(description='Prepare upstream openGym iOS build for iPhone 18 Pro')
    ap.add_argument('--root', default='.', help='Path to DuarteSantos8/openGym checkout')
    ap.add_argument('--bundle-id', default=os.environ.get('APP_BUNDLE_ID', 'com.personal.opengym.iphone18pro'))
    ap.add_argument('--app-name', default='openGym 健身')
    args = ap.parse_args()
    print(json.dumps(prepare(Path(args.root), args.bundle_id, args.app_name), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
