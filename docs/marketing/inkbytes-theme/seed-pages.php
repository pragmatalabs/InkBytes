<?php
/**
 * One-shot: create the marketing Pages so page-{slug}.php templates resolve,
 * enable pretty permalinks, and confirm the inkbytes theme is active.
 * Idempotent. Run inside the WP container:
 *   docker exec -i wordpress-yybr-wordpress-1 php /tmp/seed-pages.php
 */
require '/var/www/html/wp-load.php';

$pages = array(
	'how-it-works' => 'How It Works',
	'why'          => 'Why InkBytes',
	'features'     => 'Features',
	'pricing'      => 'Pricing',
	'methodology'  => 'Methodology & Trust',
	'about'        => 'About',
	'contact'      => 'Contact',
	'privacy'      => 'Privacy Policy',
	'terms'        => 'Terms of Service',
	'desk'         => 'The Desk',
);

foreach ( $pages as $slug => $title ) {
	if ( get_page_by_path( $slug ) ) {
		echo "exists: $slug\n";
		continue;
	}
	$id = wp_insert_post( array(
		'post_type'      => 'page',
		'post_status'    => 'publish',
		'post_title'     => $title,
		'post_name'      => $slug,
		'post_content'   => '',
		'comment_status' => 'closed',
		'ping_status'    => 'closed',
	) );
	echo ( is_wp_error( $id ) ? "ERR $slug: " . $id->get_error_message() : "created: $slug (#$id)" ) . "\n";
}

// The Desk post, as a child of /desk → /desk/rate-cuts/
$desk = get_page_by_path( 'desk' );
if ( $desk && ! get_page_by_path( 'desk/rate-cuts' ) ) {
	$id = wp_insert_post( array(
		'post_type'      => 'page',
		'post_status'    => 'publish',
		'post_title'     => 'What a coordinated rate-cut signal actually means',
		'post_name'      => 'rate-cuts',
		'post_parent'    => $desk->ID,
		'post_content'   => '',
		'comment_status' => 'closed',
		'ping_status'    => 'closed',
	) );
	echo ( is_wp_error( $id ) ? "ERR rate-cuts: " . $id->get_error_message() : "created: desk/rate-cuts (#$id)" ) . "\n";
} else {
	echo "exists or no-desk: rate-cuts\n";
}

// Pretty permalinks so /about/ etc. resolve (Pages use hierarchical paths).
if ( get_option( 'permalink_structure' ) !== '/%postname%/' ) {
	update_option( 'permalink_structure', '/%postname%/' );
	echo "permalink_structure set to /%postname%/\n";
}
flush_rewrite_rules( true );
echo "rewrite rules flushed\n";

echo 'active theme: ' . get_option( 'stylesheet' ) . ' / template: ' . get_option( 'template' ) . "\n";
