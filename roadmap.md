# Roadmap

## Near Term
- Validate apk-based installations on multiple postmarketOS devices and document any device-specific steps.
- ✅ Expand the package translation table as additional dependencies are encountered during component installs; track follow-up actions for packages without Alpine ports (`packagekit`, `libcamera-apps-lite`).

## Mid Term
- Introduce automated detection for other lightweight distributions (e.g., OpenWrt derivatives) while keeping Debian compatibility intact.
- Provide localized documentation updates mirroring the primary README changes.

## Long Term
- Explore a plugin-based dependency resolver so that package translations can be shipped without touching the core logic.
- Build a continuous integration smoke test that exercises the installer on both Debian and Alpine containers.
