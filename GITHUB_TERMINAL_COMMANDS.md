# GitHub Terminal Commands

```bash
cd ~/Downloads

rm -rf SportShield_Git_Clean
mkdir SportShield_Git_Clean

unzip -o CommunitySportsInjuryRiskAnalyzer_Local_All_Files.zip -d SportShield_Git_Clean

cd SportShield_Git_Clean/CommunitySportsInjuryRiskAnalyzer_Local

git init
git branch -M main

git add -A
git diff --cached --name-only

git commit -m "feat: add SportShield community sports injury risk analyzer"

git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/shaunakmirajgaonkar/community-sports-injury-risk-analyzer.git

git push -u origin main
```

Verify:

```bash
git status
git ls-files
git remote -v
```

Use `--force` only when intentionally replacing existing remote history.
