<?php
/**
 * InkBytes marketing theme (v2) — setup, assets, helpers.
 *
 * Self-contained: the InkBytes Design System token layer is reconstructed in
 * style.css and the DS React widgets are rendered as static HTML parts, so the
 * theme has no runtime React/Babel/CDN dependency.
 *
 * @package InkBytes
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/* ── Reader CTA target (single source of truth) ─────────────────── */
if ( ! defined( 'INKBYTES_READER_URL' ) ) {
	define( 'INKBYTES_READER_URL', 'https://inkbytes.org' );
}
function inkbytes_reader_url() {
	return apply_filters( 'inkbytes_reader_url', INKBYTES_READER_URL );
}

/* ── Internal permalink helper (slug → URL) ─────────────────────── */
function ib_url( $slug = '' ) {
	$slug = trim( (string) $slug, '/' );
	if ( $slug === '' || $slug === 'home' ) {
		return home_url( '/' );
	}
	return home_url( '/' . $slug . '/' );
}

/* ── Path to a bundled illustration ─────────────────────────────── */
function ib_illustration( $name ) {
	return get_theme_file_uri( 'assets/illustrations/' . $name . '.svg' );
}

/* ── Static outlet logo (replaces DS <OutletLogo>) ──────────────── */
function ib_outlet_logo( $id ) {
	$map = array(
		'reuters'   => array( 'R',   '#ff8000', '#fff' ),
		'ap'        => array( 'AP',  '#e9482f', '#fff' ),
		'bloomberg' => array( 'B',   '#12100f', '#fff' ),
		'guardian'  => array( 'G',   '#052962', '#fff' ),
		'ft'        => array( 'FT',  '#f3d7c9', '#33312e' ),
		'cnbc'      => array( 'C',   '#005594', '#fff' ),
		'wsj'       => array( 'WSJ', '#12100f', '#fff' ),
	);
	$d = isset( $map[ $id ] ) ? $map[ $id ] : array( strtoupper( substr( $id, 0, 1 ) ), '#333', '#fff' );
	return '<span class="dsx-logo" title="' . esc_attr( ucwords( $id ) ) . '" style="background:' . esc_attr( $d[1] ) . ';color:' . esc_attr( $d[2] ) . '">' . esc_html( $d[0] ) . '</span>';
}

/* ── Static coverage sparkline (replaces DS <Coverage>/<Sparkline>) */
function ib_sparkline() {
	return '<svg class="dsx-spark" viewBox="0 0 64 22" aria-hidden="true"><polyline points="0,21 7.1,19.8 14.2,20.6 21.3,17.7 28.4,18.9 35.6,12.7 42.7,6.5 49.8,7.8 56.9,2 64,4.1"/><circle cx="64" cy="4.1" r="1.8"/></svg>';
}

/* ── Current page key (for active nav + SEO lookup) ─────────────── */
function ib_current_key() {
	if ( is_front_page() ) {
		return 'home';
	}
	if ( is_404() ) {
		return '404';
	}
	$obj = get_queried_object();
	if ( $obj && isset( $obj->post_name ) ) {
		return $obj->post_name;
	}
	return '';
}

/* ── Per-route SEO (mirror of WORDPRESS-CONTENT.md) ─────────────── */
function ib_seo() {
	$base = get_bloginfo( 'name' );
	$map  = array(
		'home'         => array( 'InkBytes — Your Source for Comprehensive News', 'One elegant page per event, synthesized from many trusted sources. Skip the noise. Ad-free, citation-traceable news. $9/month.' ),
		'how-it-works' => array( 'How InkBytes Works — Multi-Source News Synthesis', 'A reproducible five-stage pipeline — collect, enrich, cluster, synthesize, verify — with a hard ≥2-source rule. Not a wrapper over a chatbot.' ),
		'why'          => array( 'Why InkBytes — Unbiased, Multi-Source News', 'The gap between aggregators, chatbots, and reading it all yourself. Synthesis you can trust because you can check the sources.' ),
		'features'     => array( 'Features — InkBytes', 'Cited claims, entity context, bilingual coverage, no ads, installable app, and a grounded corpus assistant.' ),
		'pricing'      => array( 'Pricing — InkBytes', 'One simple plan. Headlines free; full multi-source synthesis, citations, and entity context for $9/month. No ads, cancel anytime.' ),
		'about'        => array( 'About InkBytes', 'A paid, ad-free news reader. Each event gets one elegant, source-cited page. Built in the Dominican Republic — LATAM + global English coverage.' ),
		'methodology'  => array( 'Methodology & Trust — How InkBytes Sources and Verifies', 'Where our news comes from, the ≥2-source rule, how we avoid hallucination, how we handle bias, and how to report a correction.' ),
		'desk'         => array( 'The Desk — InkBytes Editorial & Analysis', 'Cited daily and weekly analysis across politics, world, business, technology, and more — plus methodology notes and product updates.' ),
		'rate-cuts'    => array( 'The rate-cut chorus is real — the coordination is mostly coincidence — The Desk · InkBytes', 'Three central banks moved toward easing in the same week. Read across twenty outlets, the coordinated shift looks less like a plan and more like the same data landing everywhere at once.' ),
		'contact'      => array( 'Contact — InkBytes', 'Get in touch, report a correction, or reach us for press.' ),
		'privacy'      => array( 'Privacy Policy — InkBytes', 'What InkBytes collects, how we handle it, and the privacy-first posture behind the product. No selling data, minimal analytics.' ),
		'terms'        => array( 'Terms of Service — InkBytes', 'Subscription terms, acceptable use, attribution to source content, disclaimers, and cancellation for InkBytes.' ),
		'404'          => array( 'Nothing here yet — InkBytes', '' ),
	);
	$key = ib_current_key();
	if ( isset( $map[ $key ] ) ) {
		return array( 'title' => $map[ $key ][0], 'desc' => $map[ $key ][1], 'noindex' => ( $key === '404' ) );
	}
	return array( 'title' => ( $base ? $base : 'InkBytes' ), 'desc' => get_bloginfo( 'description' ), 'noindex' => false );
}

/* ── Theme setup ────────────────────────────────────────────────── */
add_action( 'after_setup_theme', function () {
	add_theme_support( 'html5', array( 'style', 'script', 'navigation-widgets', 'search-form' ) );
	add_theme_support( 'post-thumbnails' );
	add_theme_support( 'automatic-feed-links' );
	// title-tag intentionally OFF — header.php emits a per-route <title> from ib_seo().
} );

/* ── Assets: fonts → tokens(style.css) → site.css (order matters) ─ */
add_action( 'wp_enqueue_scripts', function () {
	wp_enqueue_style(
		'inkbytes-fonts',
		'https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700;800;900&family=Spectral:ital,wght@0,400;0,500;0,600;1,400;1,500&family=IBM+Plex+Mono:wght@400;500;600&display=swap',
		array(),
		null
	);
	$ver = wp_get_theme()->get( 'Version' );
	wp_enqueue_style( 'inkbytes-tokens', get_stylesheet_uri(), array( 'inkbytes-fonts' ), $ver );
	wp_enqueue_style( 'inkbytes-site', get_theme_file_uri( 'assets/site.css' ), array( 'inkbytes-tokens' ), $ver );
	wp_enqueue_style( 'inkbytes-widgets', get_theme_file_uri( 'assets/widgets.css' ), array( 'inkbytes-site' ), $ver );
} );

/* ── Preconnect to the font hosts ───────────────────────────────── */
add_filter( 'wp_resource_hints', function ( $hints, $relation ) {
	if ( 'preconnect' === $relation ) {
		$hints[] = 'https://fonts.googleapis.com';
		$hints[] = array( 'href' => 'https://fonts.gstatic.com', 'crossorigin' );
	}
	return $hints;
}, 10, 2 );

/* ── Lean <head> (idempotent with the hardening mu-plugin) ──────── */
add_action( 'init', function () {
	remove_action( 'wp_head', 'wp_generator' );
	remove_action( 'wp_head', 'rsd_link' );
	remove_action( 'wp_head', 'wlwmanifest_link' );
	remove_action( 'wp_head', 'wp_shortlink_wp_head' );
	remove_action( 'wp_head', 'rest_output_link_wp_head' );
	remove_action( 'wp_head', 'wp_oembed_add_discovery_links' );
} );
