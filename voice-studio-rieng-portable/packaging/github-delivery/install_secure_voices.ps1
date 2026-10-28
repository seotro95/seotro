param(
    [string]$PackageRoot = $PSScriptRoot,
    [Security.SecureString]$SecurePassword,
    [string]$Password = '',
    [string]$Target = '',
    [switch]$DecryptOnly,
    [string]$OutputPath = '',
    [switch]$InputSelfTest
)

$ErrorActionPreference = 'Stop'

function ConvertTo-InteractiveVoicePassword([string]$Value) {
    $normalized = $Value.Trim()
    if ($normalized -cnotmatch '^[0-9a-fA-F]{32}$') {
        throw 'Mat khau can du 32 ky tu. Hay sao chep mat khau trong chat va bam Dan mat khau.'
    }
    return $normalized.ToLowerInvariant()
}

function Set-VoicePasswordFieldFromClipboard([object]$Dialog, [scriptblock]$ClipboardReader) {
    # This is called only by the explicit Paste button, never on dialog creation.
    $copied = [string](& $ClipboardReader)
    $Dialog.TextBox.Text = $copied.Trim()
    $Dialog.TextBox.SelectionStart = $Dialog.TextBox.TextLength
    $Dialog.TextBox.Focus() | Out-Null
}

function New-VoicePasswordDialog {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    [Windows.Forms.Application]::EnableVisualStyles()
    $form = [Windows.Forms.Form]::new()
    $form.Text = 'Voice Studio - Cai 19 giong'
    $form.ClientSize = [Drawing.Size]::new(590, 270)
    $form.StartPosition = [Windows.Forms.FormStartPosition]::CenterScreen
    $form.FormBorderStyle = [Windows.Forms.FormBorderStyle]::FixedDialog
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.Font = [Drawing.Font]::new('Segoe UI', 10)

    $instructions = [Windows.Forms.Label]::new()
    $instructions.Location = [Drawing.Point]::new(20, 16)
    $instructions.Size = [Drawing.Size]::new(550, 48)
    $instructions.Text = "Sao chep mat khau trong cuoc tro chuyen, roi bam Dan mat khau.`r`nKiem tra du 32 ky tu va bam Cai 19 giong."
    $box = [Windows.Forms.TextBox]::new()
    $box.Location = [Drawing.Point]::new(20, 76)
    $box.Size = [Drawing.Size]::new(550, 30)
    $box.MaxLength = 256
    $box.UseSystemPasswordChar = $true
    $box.ShortcutsEnabled = $true
    $paste = [Windows.Forms.Button]::new()
    $paste.Text = 'Dan mat khau'
    $paste.Location = [Drawing.Point]::new(20, 118)
    $paste.Size = [Drawing.Size]::new(140, 34)
    $show = [Windows.Forms.CheckBox]::new()
    $show.Text = 'Hien mat khau'
    $show.Location = [Drawing.Point]::new(180, 123)
    $show.Size = [Drawing.Size]::new(160, 26)
    $count = [Windows.Forms.Label]::new()
    $count.Location = [Drawing.Point]::new(20, 166)
    $count.Size = [Drawing.Size]::new(550, 28)
    $count.Text = 'Da nhap: 0/32 ky tu'
    $install = [Windows.Forms.Button]::new()
    $install.Text = 'Cai 19 giong'
    $install.Location = [Drawing.Point]::new(276, 214)
    $install.Size = [Drawing.Size]::new(140, 36)
    $install.Enabled = $false
    $cancel = [Windows.Forms.Button]::new()
    $cancel.Text = 'Huy'
    $cancel.Location = [Drawing.Point]::new(430, 214)
    $cancel.Size = [Drawing.Size]::new(140, 36)
    $cancel.DialogResult = [Windows.Forms.DialogResult]::Cancel
    $form.Controls.AddRange([Windows.Forms.Control[]]@($instructions, $box, $paste, $show, $count, $install, $cancel))
    $form.AcceptButton = $install
    $form.CancelButton = $cancel
    $state = [PSCustomObject]@{
        Form = $form; TextBox = $box; PasteButton = $paste; ShowCheckBox = $show
        CountLabel = $count; InstallButton = $install; CancelButton = $cancel
        AcceptedPassword = $null; ClipboardReader = { [Windows.Forms.Clipboard]::GetText() }
        PasteAction = $null; SuppressMessageBoxes = $false
    }
    $normalizePassword = ${function:ConvertTo-InteractiveVoicePassword}
    $pasteToField = ${function:Set-VoicePasswordFieldFromClipboard}
    $box.Add_TextChanged({
        $value = $state.TextBox.Text.Trim()
        $valid = $value -cmatch '^[0-9a-fA-F]{32}$'
        $state.CountLabel.Text = ('Da nhap: {0}/32 ky tu' -f $value.Length)
        $state.CountLabel.ForeColor = if ($valid) { [Drawing.Color]::DarkGreen } else { [Drawing.Color]::DarkRed }
        $state.InstallButton.Enabled = $valid
    }.GetNewClosure())
    $show.Add_CheckedChanged({ $state.TextBox.UseSystemPasswordChar = -not $state.ShowCheckBox.Checked }.GetNewClosure())
    $state.PasteAction = {
        try { & $pasteToField $state $state.ClipboardReader }
        catch {
            if ($state.SuppressMessageBoxes) { throw }
            [Windows.Forms.MessageBox]::Show('Chua doc duoc noi dung da sao chep. Hay sao chep mat khau va bam Dan mat khau lai.', 'Voice Studio') | Out-Null
        }
    }.GetNewClosure()
    $paste.Add_Click($state.PasteAction)
    $install.Add_Click({
        try {
            $state.AcceptedPassword = & $normalizePassword $state.TextBox.Text
            $state.Form.DialogResult = [Windows.Forms.DialogResult]::OK
            $state.Form.Close()
        } catch { [Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Voice Studio') | Out-Null }
    }.GetNewClosure())
    return $state
}

function Read-InteractiveVoicePassword {
    $state = New-VoicePasswordDialog
    try {
        if ($state.Form.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) { return $null }
        return $state.AcceptedPassword
    } finally {
        $state.AcceptedPassword = $null
        $state.TextBox.Clear()
        $state.Form.Dispose()
    }
}

function Test-VoicePasswordInput {
    $state = New-VoicePasswordDialog
    try {
        $state.SuppressMessageBoxes = $true
        if ($state.InstallButton.Enabled -or $state.TextBox.TextLength -ne 0) { throw 'Empty input must not enable installation.' }
        $state.ClipboardReader = { '  ABCDEF0123456789ABCDEF0123456789  ' }
        & $state.PasteAction
        if ($state.TextBox.Text -cne 'ABCDEF0123456789ABCDEF0123456789' -or -not $state.InstallButton.Enabled -or
            $state.CountLabel.Text -ne 'Da nhap: 32/32 ky tu') { throw 'Paste action or length validation failed.' }
        if ((ConvertTo-InteractiveVoicePassword $state.TextBox.Text) -cne 'abcdef0123456789abcdef0123456789') { throw 'Interactive normalization failed.' }
        $state.ShowCheckBox.Checked = $true
        if ($state.TextBox.UseSystemPasswordChar) { throw 'Show-password control failed.' }
        $state.ShowCheckBox.Checked = $false
        if (-not $state.TextBox.UseSystemPasswordChar) { throw 'Password masking control failed.' }
        $state.TextBox.Text = 'x'
        if ($state.InstallButton.Enabled -or $state.CountLabel.Text -ne 'Da nhap: 1/32 ky tu') { throw 'Short input must be refused.' }
        $state.TextBox.Text = 'z' * 32
        if ($state.InstallButton.Enabled) { throw 'Non-hex input must be refused.' }
        if ($null -ne $state.AcceptedPassword -or $state.CancelButton.DialogResult -ne [Windows.Forms.DialogResult]::Cancel) { throw 'Cancellation state is invalid.' }
        Write-Host 'Windows password input controls and paste validation passed. No private password or clipboard was used.'
    } finally { $state.TextBox.Clear(); $state.Form.Dispose() }
}

function Read-ExactBytes([IO.Stream]$Stream, [int]$Count) {
    [byte[]]$buffer = New-Object byte[] $Count
    $offset = 0
    while ($offset -lt $Count) {
        $read = $Stream.Read($buffer, $offset, $Count - $offset)
        if ($read -eq 0) { throw 'Goi giong bi cat ngan. Hay tai lai tu GitHub.' }
        $offset += $read
    }
    return ,$buffer
}

function Get-LowerHex([byte[]]$Bytes) {
    return [BitConverter]::ToString($Bytes).Replace('-', '').ToLowerInvariant()
}

function Get-FileSha256([string]$Path) {
    $stream = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return Get-LowerHex ($sha.ComputeHash($stream)) }
    finally { $sha.Dispose(); $stream.Dispose() }
}

function Read-DeliveryManifest([string]$Root) {
    $manifestPath = Join-Path $Root 'delivery\manifest.json'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.format -ne 'voice-studio-private-delivery-v1' -or
        $manifest.encrypted_file -ne 'voices.vspack' -or
        $manifest.updater_root -ne 'Voice-Studio-Rieng-1.7.0-Cap-Nhat-19-Giong' -or
        $manifest.encrypted_sha256 -cnotmatch '^[0-9a-f]{64}$' -or
        $manifest.plaintext_sha256 -cnotmatch '^[0-9a-f]{64}$') {
        throw 'Thong tin goi giong khong hop le. Hay tai lai ban day du tu GitHub.'
    }
    [long]$encryptedSize = $manifest.encrypted_size
    [long]$plainSize = $manifest.plaintext_size
    if ($encryptedSize -lt 96 -or $encryptedSize -gt 268435456 -or
        $plainSize -lt 1 -or $plainSize -gt 268435456 -or
        (($encryptedSize - 80) % 16) -ne 0) {
        throw 'Kich thuoc goi giong khong hop le.'
    }
    return $manifest
}

function Unprotect-VoicePackage([string]$Root, [string]$PlainPassword, [string]$Destination) {
    $manifest = Read-DeliveryManifest $Root
    $packetPath = Join-Path $Root 'delivery\voices.vspack'
    $destinationPath = [IO.Path]::GetFullPath($Destination)
    if ([IO.File]::Exists($destinationPath) -or [IO.Directory]::Exists($destinationPath)) {
        throw 'Tep dich da ton tai. Khong ghi de du lieu cu.'
    }
    $inputFile = $null; $derivation = $null; $hmac = $null; $aes = $null
    $decryptor = $null; $writer = $null; $cryptoStream = $null; $pending = $null
    $keyMaterial = $null; $aesKey = $null; $macKey = $null
    try {
        # Keep this read handle open through authentication and decryption.
        # FileShare.Read prevents another Windows process from changing it.
        $inputFile = [IO.File]::Open($packetPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
        if ($inputFile.Length -ne [long]$manifest.encrypted_size) {
            throw 'Goi giong chua tai du. Hay tai lai tu GitHub.'
        }
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $actualHash = Get-LowerHex ($sha.ComputeHash($inputFile)) }
        finally { $sha.Dispose() }
        if ($actualHash -cne $manifest.encrypted_sha256) {
            throw 'SHA256 goi giong khong khop. Hay tai lai tu GitHub.'
        }
        $inputFile.Position = 0
        [byte[]]$header = Read-ExactBytes $inputFile 48
        if ([Text.Encoding]::ASCII.GetString($header, 0, 8) -cne 'VSPACK01') {
            throw 'Dinh dang goi giong khong dung.'
        }
        if (-not [BitConverter]::IsLittleEndian) { throw 'Nen tang nay khong duoc ho tro.' }
        [uint64]$declaredLength = [BitConverter]::ToUInt64($header, 40)
        if ($declaredLength -ne [uint64]$manifest.plaintext_size) {
            throw 'Kich thuoc goc trong goi giong khong khop.'
        }
        [byte[]]$salt = $header[8..23]
        [byte[]]$iv = $header[24..39]
        $derivation = [Security.Cryptography.Rfc2898DeriveBytes]::new(
            $PlainPassword, $salt, 200000, [Security.Cryptography.HashAlgorithmName]::SHA256)
        [byte[]]$keyMaterial = $derivation.GetBytes(64)
        [byte[]]$aesKey = $keyMaterial[0..31]
        [byte[]]$macKey = $keyMaterial[32..63]
        $hmac = [Security.Cryptography.HMACSHA256]::new($macKey)
        $null = $hmac.TransformBlock($header, 0, $header.Length, $header, 0)
        [long]$cipherLength = $inputFile.Length - 80
        [long]$remaining = $cipherLength
        [byte[]]$buffer = New-Object byte[] 1048576
        while ($remaining -gt 0) {
            $count = [int][Math]::Min([long]$buffer.Length, $remaining)
            $read = $inputFile.Read($buffer, 0, $count)
            if ($read -eq 0) { throw 'Goi giong bi cat ngan.' }
            $null = $hmac.TransformBlock($buffer, 0, $read, $buffer, 0)
            $remaining -= $read
        }
        $null = $hmac.TransformFinalBlock([byte[]]@(), 0, 0)
        [byte[]]$storedTag = Read-ExactBytes $inputFile 32
        [byte[]]$calculatedTag = $hmac.Hash
        $difference = 0
        for ($index = 0; $index -lt 32; $index++) {
            $difference = $difference -bor ($storedTag[$index] -bxor $calculatedTag[$index])
        }
        if ($difference -ne 0) {
            throw 'Mat khau chua khop. Hay sao chep mat khau trong chat, mo lai cua so cai va bam Dan mat khau. Khong cai dat tep nao.'
        }

        # No plaintext file is created until the complete MAC has passed.
        $parent = [IO.Path]::GetDirectoryName($destinationPath)
        $null = [IO.Directory]::CreateDirectory($parent)
        $pending = Join-Path $parent ('.voice-decrypt-' + [Guid]::NewGuid().ToString('N') + '.tmp')
        $writer = [IO.File]::Open($pending, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        $aes = [Security.Cryptography.Aes]::Create()
        $aes.KeySize = 256
        $aes.Mode = [Security.Cryptography.CipherMode]::CBC
        $aes.Padding = [Security.Cryptography.PaddingMode]::PKCS7
        $aes.Key = $aesKey
        $aes.IV = $iv
        $decryptor = $aes.CreateDecryptor()
        $cryptoStream = [Security.Cryptography.CryptoStream]::new($writer, $decryptor, [Security.Cryptography.CryptoStreamMode]::Write)
        $inputFile.Position = 48
        $remaining = $cipherLength
        while ($remaining -gt 0) {
            $count = [int][Math]::Min([long]$buffer.Length, $remaining)
            $read = $inputFile.Read($buffer, 0, $count)
            if ($read -eq 0) { throw 'Goi giong bi cat ngan.' }
            $cryptoStream.Write($buffer, 0, $read)
            $remaining -= $read
        }
        $cryptoStream.FlushFinalBlock()
        $cryptoStream.Dispose(); $cryptoStream = $null
        $writer.Dispose(); $writer = $null
        if ((Get-Item -LiteralPath $pending).Length -ne [long]$manifest.plaintext_size -or
            (Get-FileSha256 $pending) -cne $manifest.plaintext_sha256) {
            throw 'Tep giong sau giai ma khong khop. Khong cai dat tep nao.'
        }
        [IO.File]::Move($pending, $destinationPath)
        $pending = $null
        return $manifest
    } finally {
        # Failed padding or an I/O error may also make Dispose throw. Attempt
        # every cleanup operation without replacing the original error.
        foreach ($resource in @($cryptoStream, $writer, $decryptor, $aes, $hmac, $derivation, $inputFile)) {
            if ($null -ne $resource) { try { $resource.Dispose() } catch {} }
        }
        foreach ($key in @($keyMaterial, $aesKey, $macKey)) {
            if ($null -ne $key) { [Array]::Clear($key, 0, $key.Length) }
        }
        if ($pending -and [IO.File]::Exists($pending)) { try { [IO.File]::Delete($pending) } catch {} }
    }
}

$privateTemporary = $null
try {
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
    if ($InputSelfTest) { Test-VoicePasswordInput; exit 0 }
    $root = [IO.Path]::GetFullPath($PackageRoot)
    if ($DecryptOnly -and [string]::IsNullOrWhiteSpace($OutputPath)) {
        throw 'Can chi dinh OutputPath khi kiem tra giai ma.'
    }
    if (-not $DecryptOnly) {
        if (-not [IO.File]::Exists((Join-Path $root 'delivery\manifest.json')) -or
            -not [IO.File]::Exists((Join-Path $root 'delivery\voices.vspack'))) {
            Add-Type -AssemblyName System.Windows.Forms
            $sourceDialog = [Windows.Forms.FolderBrowserDialog]::new()
            try {
                $sourceDialog.Description = 'Chon thu muc ban day du da giai nen, co app, runtime va delivery.'
                $sourceDialog.ShowNewFolderButton = $false
                if ($sourceDialog.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) {
                    Write-Host 'Da huy cai dat; khong thay doi tep nao.'
                    exit 0
                }
                $root = [IO.Path]::GetFullPath($sourceDialog.SelectedPath)
            } finally { $sourceDialog.Dispose() }
            if (-not [IO.File]::Exists((Join-Path $root 'delivery\manifest.json')) -or
                -not [IO.File]::Exists((Join-Path $root 'delivery\voices.vspack'))) {
                throw 'Hay chon dung thu muc ban day du co thu muc delivery. Khong can tai lai file ZIP lon.'
            }
        }
        $targetRoot = $root
        if (-not [string]::IsNullOrWhiteSpace($Target)) { $targetRoot = [IO.Path]::GetFullPath($Target) }
        if (-not [IO.File]::Exists((Join-Path $targetRoot 'runtime\python.exe')) -or
            -not [IO.File]::Exists((Join-Path $targetRoot 'app\app.py'))) {
            if (-not [string]::IsNullOrWhiteSpace($Target)) {
                throw 'Thu muc Target can co runtime\python.exe va app\app.py.'
            }
            Add-Type -AssemblyName System.Windows.Forms
            $dialog = [Windows.Forms.FolderBrowserDialog]::new()
            try {
                $dialog.Description = 'Chon thu muc Voice Studio Portable da giai nen (co runtime va app).'
                $dialog.ShowNewFolderButton = $false
                if ($dialog.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) {
                    Write-Host 'Da huy cai dat; khong thay doi tep nao.'
                    exit 0
                }
                $targetRoot = [IO.Path]::GetFullPath($dialog.SelectedPath)
            } finally { $dialog.Dispose() }
            if (-not [IO.File]::Exists((Join-Path $targetRoot 'runtime\python.exe')) -or
                -not [IO.File]::Exists((Join-Path $targetRoot 'app\app.py'))) {
                throw 'Hay chon thu muc tool da giai nen day du, co runtime va app.'
            }
        }
        $python = Join-Path $targetRoot 'runtime\python.exe'
        Write-Host 'Dong Voice Studio truoc khi cai 19 giong. Lich su va model hien co duoc giu lai.'
    }
    if ($SecurePassword -and -not [string]::IsNullOrEmpty($Password)) {
        throw 'Chi su dung mot cach nhap mat khau.'
    }
    if ([string]::IsNullOrEmpty($Password)) {
        if ($SecurePassword) {
            $address = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
            try { $Password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($address) }
            finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($address) }
        } else {
            $Password = Read-InteractiveVoicePassword
            if ([string]::IsNullOrEmpty($Password)) {
                Write-Host 'Da huy cai dat; khong thay doi tep nao.'
                exit 0
            }
        }
    }
    if ([string]::IsNullOrEmpty($Password)) { throw 'Chua nhap mat khau.' }
    if ($DecryptOnly) {
        $null = Unprotect-VoicePackage $root $Password $OutputPath
        Write-Host 'Kiem tra giai ma thanh cong.'
    } else {
        $privateTemporary = Join-Path $targetRoot ('.voice-install-' + [Guid]::NewGuid().ToString('N'))
        $null = [IO.Directory]::CreateDirectory($privateTemporary)
        $plainZip = Join-Path $privateTemporary 'voice-update.zip'
        $manifest = Unprotect-VoicePackage $root $Password $plainZip
        $Password = $null
        $extracted = Join-Path $privateTemporary 'extracted'
        Expand-Archive -LiteralPath $plainZip -DestinationPath $extracted
        $installer = Join-Path (Join-Path $extracted $manifest.updater_root) 'install_update.py'
        if (-not [IO.File]::Exists($installer)) { throw 'Goi cap nhat thieu chuong trinh cai dat.' }
        $env:PYTHONUTF8 = '1'; $env:PYTHONNOUSERSITE = '1'
        Remove-Item Env:PYTHONHOME, Env:PYTHONPATH -ErrorAction SilentlyContinue
        & $python -s -X utf8 $installer --target $targetRoot
        if ($LASTEXITCODE -ne 0) { throw 'Chua cai xong. Xem thong bao ben tren, dong tool roi thu lai.' }
        Write-Host 'Da cai 19 giong mac dinh. Mo MO_TOOL.bat de nghe thu va su dung.'
        Write-Host 'Cac giong quoc te moi can chay TAI_GIONG_DA_NGON_NGU.bat mot lan de tai model.'
    }
    exit 0
} catch {
    Write-Host ('Khong cai duoc goi giong: ' + $_.Exception.Message)
    exit 1
} finally {
    $Password = $null
    if ($privateTemporary -and [IO.Directory]::Exists($privateTemporary)) {
        Remove-Item -LiteralPath $privateTemporary -Recurse -Force -ErrorAction SilentlyContinue
    }
}
