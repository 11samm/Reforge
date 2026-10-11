# Interaction map and bounded inspection

The local map is a versioned JSON graph under evidence/feature-memory/ui-<target-hash>.json.
It stores locations, successful exploration action paths, observed controls/domains,
observation provenance, timestamps and validated discovery routes. Exploration paths
are visited actions, not guaranteed reusable navigation. Only a grounded specification
can become a cached route. UI data is untrusted navigation knowledge, not pixel behavior
evidence. Target name/version/build partitions maps; hosted unpinned builds still require
fresh checks. Prior nodes become stale when a new discovery session loads the map.

The model can use map_query(query,parent,page), returning eight nodes per page, and
map_route(feature), returning one cached route as a hint. It must replay visible actions,
inspect fresh values and cite current observation IDs before declaring discovery. Old
observation IDs are rejected by existing grounding. Routes are never executed implicitly
or substituted for current reference evidence. Current limitations include Contrast-only
route support and one active browser owner.

visible_click and visible_set now return a small action acknowledgement, not a new full
page snapshot. The model must inspect after actions. visible_inspect(scope,dialog,page)
supports the full visible page or active dialog, with auto preferring the active dialog.
Page zero captures a bounded stable snapshot; subsequent pages retrieve that snapshot.
An action invalidates it. Every accessibility character and projected control is reachable
through pages; no controls are silently dropped at the old 150-element cutoff. Individual
oversized items and snapshots exceeding 2000 controls stop explicitly. Numeric dialog
facts cannot ground a completed specification until all relevant snapshot pages have been
inspected. Only delivered control pages enter current model observation evidence/maps.

Per-response text remains 16 KB, with unchanged time/action/observation/tool budgets and
1.8 MB cumulative output limit. Snapshot archives separately share a 1.8 MB cumulative
storage bound. Map storage is capped at 300 KB, 500 nodes and eight routes. Hitting a
capacity stops explicitly; arbitrary browser code, selectors and filesystem paths remain
unavailable to the model. Pages and queries all consume the bounded tool budget.

Offline tests cover cross-session persistence and stale status, target changes, route
invalidation, complete lossless paging, large menu actions, dialog focus, snapshot
invalidation, rejection of incomplete dialog evidence and bounded query behavior.
No live discovery or learning pilot was run for this implementation.
