<?php
/**
 * InkBytes marketing theme — setup & assets.
 *
 * @package InkBytes
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/** Where the "Start reading" / "Browse" CTAs point (the actual reader app). */
if ( ! defined( 'INKBYTES_READER_URL' ) ) {
	define( 'INKBYTES_READER_URL', 'https://inkbytes.org' );
}

/** Helper so templates don't hardcode the reader URL. */
function inkbytes_reader_url() {
	return apply_filters( 'inkbytes_reader_url', INKBYTES_READER_URL );
}

/**
 * Theme supports. Note: title-tag is intentionally OFF — header.php sets a
 * fixed marketing <title> so it always reads exactly as designed.
 */
add_action( 'after_setup_theme', function () {
	add_theme_support( 'html5', array( 'style', 'script', 'navigation-widgets' ) );
	add_theme_support( 'automatic-feed-links' );
} );

/** Fonts + theme stylesheet. */
add_action( 'wp_enqueue_scripts', function () {
	wp_enqueue_style(
		'inkbytes-fonts',
		'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&display=swap',
		array(),
		null
	);
	wp_enqueue_style(
		'inkbytes-style',
		get_stylesheet_uri(),
		array( 'inkbytes-fonts' ),
		wp_get_theme()->get( 'Version' )
	);
} );

/** Preconnect to Google Fonts hosts (matches the original page's <link rel=preconnect>). */
add_filter( 'wp_resource_hints', function ( $hints, $relation ) {
	if ( 'preconnect' === $relation ) {
		$hints[] = 'https://fonts.googleapis.com';
		$hints[] = array( 'href' => 'https://fonts.gstatic.com', 'crossorigin' );
	}
	return $hints;
}, 10, 2 );

/** Keep the <head> lean for a marketing page (mirrors the mu-plugin hardening). */
add_action( 'init', function () {
	remove_action( 'wp_head', 'wp_generator' );
	remove_action( 'wp_head', 'rsd_link' );
	remove_action( 'wp_head', 'wlwmanifest_link' );
	remove_action( 'wp_head', 'wp_shortlink_wp_head' );
	remove_action( 'wp_head', 'rest_output_link_wp_head' );
	remove_action( 'wp_head', 'wp_oembed_add_discovery_links' );
} );
