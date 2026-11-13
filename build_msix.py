import os
import shutil
import subprocess
from PIL import Image

staging = r'c:\Users\arvin\OneDrive\Desktop\TaxClean - AntiGravity\msix_staging'
src = r'c:\Users\arvin\OneDrive\Desktop\TaxClean - AntiGravity\dist\TaxCleanZA'
out_msix = r'c:\Users\arvin\OneDrive\Desktop\TaxClean - AntiGravity\dist\TaxCleanZA.msix'

import zipfile
from pathlib import Path

# Ensure _tcl_data and _tk_data are extracted on disk inside dist/TaxCleanZA/_internal
# so WindowsApps ACLs and Microsoft Store Authenticode DLL signing never break Tcl 9.0 zipfs
internal_dir = Path(src) / '_internal'
for dll_name, zip_prefix, target_folder in [
    ('tcl90.dll', 'tcl_library/', '_tcl_data'),
    ('tcl9tk90.dll', 'tk_library/', '_tk_data'),
]:
    dll_path = internal_dir / dll_name
    if dll_path.exists() and zipfile.is_zipfile(dll_path):
        with zipfile.ZipFile(dll_path) as zf:
            for member in zf.namelist():
                if member.startswith(zip_prefix) and not member.endswith('/'):
                    rel_path = member[len(zip_prefix):]
                    dest_path = internal_dir / target_folder / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    dest_path.write_bytes(zf.read(member))
print("Verified _tcl_data and _tk_data extracted in dist/TaxCleanZA/_internal")

if os.path.exists(staging):
    shutil.rmtree(staging)
shutil.copytree(src, staging)

assets_dir = os.path.join(staging, 'Assets')
os.makedirs(assets_dir, exist_ok=True)

logo_path = r'c:\Users\arvin\OneDrive\Desktop\TaxClean - AntiGravity\store_assets\1_Box_Art_Logo_1080x1080.png'
img = Image.open(logo_path).convert('RGBA')

sizes = {
    'StoreLogo.png': (50, 50),
    'Square44x44Logo.png': (44, 44),
    'Square150x150Logo.png': (150, 150),
    'Square310x310Logo.png': (310, 310),
}
for name, sz in sizes.items():
    resized = img.resize(sz, Image.Resampling.LANCZOS)
    resized.save(os.path.join(assets_dir, name), 'PNG')

wide = Image.new('RGBA', (310, 150), (15, 23, 42, 255))
icon_120 = img.resize((120, 120), Image.Resampling.LANCZOS)
wide.paste(icon_120, ((310 - 120) // 2, (150 - 120) // 2), icon_120)
wide.save(os.path.join(assets_dir, 'Wide310x150Logo.png'), 'PNG')

manifest = """<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap rescap">

  <Identity
    Name="TaxCleanZa.TaxClean-ZA"
    Publisher="CN=B92F47E2-89C8-4C28-8908-21D3DC06B5D7"
    Version="2.7.0.0"
    ProcessorArchitecture="x64" />

  <Properties>
    <DisplayName>TaxClean - ZA</DisplayName>
    <PublisherDisplayName>TaxCleanZa</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
  </Properties>

  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.22631.0" />
  </Dependencies>

  <Resources>
    <Resource Language="en-us" />
  </Resources>

  <Applications>
    <Application Id="TaxCleanZA" Executable="TaxCleanZA.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements
        DisplayName="TaxClean - ZA"
        Description="100% Offline South African Bank Statement, Receipt OCR and SARS VAT201 Automation Engine"
        BackgroundColor="#0F172A"
        Square150x150Logo="Assets\\Square150x150Logo.png"
        Square44x44Logo="Assets\\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\\Wide310x150Logo.png" Square310x310Logo="Assets\\Square310x310Logo.png" />
      </uap:VisualElements>
    </Application>
  </Applications>

  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
"""

with open(os.path.join(staging, 'AppxManifest.xml'), 'w', encoding='utf-8') as f:
    f.write(manifest)

makeappx = r'C:\Users\arvin\AppData\Local\Temp\win_sdk_buildtools\bin\10.0.28000.0\x64\makeappx.exe'
if os.path.exists(out_msix):
    os.remove(out_msix)

print("Running makeappx.exe pack...")
res = subprocess.run([makeappx, 'pack', '/d', staging, '/p', out_msix, '/o'], capture_output=True, text=True)
print(res.stdout)
if res.returncode != 0:
    print("STDERR:", res.stderr)
    raise SystemExit(res.returncode)
shutil.rmtree(staging, ignore_errors=True)
print("Successfully built:", out_msix, "Size MB:", round(os.path.getsize(out_msix) / (1024*1024), 2))
