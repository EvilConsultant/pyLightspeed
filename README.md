## Reauth Token

Run this from the pyLightspeed repo root (you need browser access to paste the redirect URL):
```
cd C:\Data\Development\Bottles\pyLightspeed

# Pull Vault creds from bottlemover .env
Get-Content C:\Data\Development\Bottles\bottlemover\.env |
  Where-Object { $_ -match '^(VAULT_ADDR|VAULT_TOKEN)=' } |
  ForEach-Object { $k,$v = $_ -split '=',2; Set-Item "env:$k" $v.Trim() }

# Point to store 2's Vault paths (match the error output exactly)
$env:VAULT_LSR_TOKEN_PATH        = "lightspeed/stores/2/tokens"
$env:VAULT_LSR_CREDENTIALS_PATHS = "lightspeed/shared,lightspeed/stores/2/creds"

uv run scripts/reauthorize_rseries.py
```
The script (scripts/reauthorize_rseries.py) will:

Detect the Vault store from the env vars and use it automatically (no prompts)
Load LSR_CLIENT_ID / LSR_CLIENT_SECRET from Vault (lightspeed/shared + lightspeed/stores/2/creds)
Open the Lightspeed auth page in your browser
Wait for you to paste back the redirect URL
Exchange the code and write the new token back to Vault at lightspeed/stores/2/tokens
After that, drnkz-migration-run will work again without any code changes.