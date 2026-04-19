---
applyTo: '**'
description: 'RTK — proxy CLI token-optimized : règle de préfixage et commandes Jarvis'
---

# RTK — Token-Optimized CLI

**rtk** filtre et compresse les sorties de commandes avant qu'elles atteignent le contexte LLM, économisant 60–90% de tokens.

- **Binaire** : `C:\Tools\rtk.exe`  
- **Hook Copilot** : `.github/hooks/rtk-rewrite.json` (PreToolUse — actif automatiquement)  
- **Documentation** : `docs/RTK.md`

## Règle : toujours préfixer avec `rtk`

```bash
# Au lieu de :           Utiliser :
git status               rtk git status
git log -n 10            rtk git log -n 10
docker ps                rtk docker ps
docker logs <name>       rtk docker logs <name>
mvn test                 rtk mvn test
mvn clean install        rtk mvn clean install
ls .                     rtk ls .
grep "pattern" .         rtk grep "pattern" .
```

## Commandes Jarvis prioritaires

```bash
# Maven (modules Quarkus)
rtk mvn clean install -pl jarvis-core
rtk mvn test -pl jarvis-worker
rtk mvn quarkus:dev

# Docker stack Jarvis
rtk docker compose -f docker/jarvis-stack/docker-compose.yml ps
rtk docker logs jarvis-core --tail 50
rtk docker logs jarvis-worker --tail 50

# Git workflow
rtk git status
rtk git log -n 10
rtk git diff
```

## Meta-commandes RTK (utiliser directement, sans préfixe)

```bash
rtk gain              # Tableau de bord économies de tokens
rtk gain --history    # Historique par commande
rtk discover          # Trouver les opportunités manquées
rtk session           # Adoption RTK sur les sessions récentes
```
