<?php

/*
|--------------------------------------------------------------------------
| Outlet Region Rules  (single source of truth)
|--------------------------------------------------------------------------
|
| A region tags an outlet for regional routing / per-region scoring in the
| entity graph and Reader feed.
|
| NAMING RULE
| -----------
|   A region is EITHER the literal "global"
|   OR  "{macro}-{cc}"  where
|        {macro} = a macro-area key from 'macros' below
|        {cc}    = the ISO 3166-1 alpha-2 country code, lowercase
|
|   Examples:  latam-dr (Dominican Republic), europe-es (Spain),
|              latam-ar (Argentina), europe-de (Germany).
|
| TO EXTEND
| ---------
|   • New country in an existing macro → add its ISO-alpha-2 code to that
|     macro's array below.  Nothing else changes.
|   • New macro area              → add a new key to 'macros'.
|   • Region that doesn't fit the macro-cc shape → add to 'standalone'.
|
|   The flat 'allowed' whitelist (consumed by OutletController validation
|   and the Backoffice region dropdown) is DERIVED from this file — never
|   hand-maintain a second list.  Adding a code here is the ONLY edit
|   needed to make it importable and selectable.
|
*/

$macros = [
    // LATAM — Spanish-language outlets, country-level granularity.
    'latam' => [
        'dr', // Dominican Republic
        'mx', // Mexico
        'co', // Colombia
        'ar', // Argentina
        'pe', // Peru
        'cl', // Chile
        'ec', // Ecuador
        'pr', // Puerto Rico
        've', // Venezuela
    ],

    // Europe — multilingual (es / fr / de …); language field discriminates.
    'europe' => [
        'es', // Spain
        'fr', // France
        'de', // Germany
    ],
];

// Regions that intentionally don't follow the {macro}-{cc} pattern.
$standalone = [
    'global', // global EN business/tech wires (CNN, AP, Reuters, BBC, …)
];

// Derive the flat whitelist. Order: standalone first, then macro-cc pairs
// grouped by macro in declaration order — stable for UI dropdowns.
$allowed = $standalone;
foreach ($macros as $macro => $countries) {
    foreach ($countries as $cc) {
        $allowed[] = "{$macro}-{$cc}";
    }
}

return [
    'macros'     => $macros,
    'standalone' => $standalone,
    'allowed'    => $allowed,
];
