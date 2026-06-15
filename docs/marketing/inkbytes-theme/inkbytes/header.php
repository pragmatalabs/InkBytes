<?php
/**
 * Header — <head>, brand sprite, and the sticky primary nav.
 * Server-rendered from assets/chrome.jsx (EN). ES is a documented fast-follow.
 *
 * @package InkBytes
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

$ib_seo = ib_seo();
$ib_key = ib_current_key();

// Primary nav: label, slug, and the active key it lights up on.
$ib_nav = array(
	array( 'label' => 'How it works', 'slug' => 'how-it-works', 'on' => array( 'how-it-works' ) ),
	array( 'label' => 'Why InkBytes', 'slug' => 'why',          'on' => array( 'why' ) ),
	array( 'label' => 'Pricing',      'slug' => 'pricing',       'on' => array( 'pricing' ) ),
	array( 'label' => 'The Desk',     'slug' => 'desk',          'on' => array( 'desk', 'rate-cuts' ) ),
	array( 'label' => 'Methodology',  'slug' => 'methodology',   'on' => array( 'methodology' ) ),
);
?><!doctype html>
<html <?php language_attributes(); ?>>
<head>
<meta charset="<?php bloginfo( 'charset' ); ?>" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title><?php echo esc_html( $ib_seo['title'] ); ?></title>
<?php if ( ! empty( $ib_seo['desc'] ) ) : ?>
<meta name="description" content="<?php echo esc_attr( $ib_seo['desc'] ); ?>" />
<?php endif; ?>
<?php if ( ! empty( $ib_seo['noindex'] ) ) : ?>
<meta name="robots" content="noindex,follow" />
<?php endif; ?>
<meta property="og:title" content="<?php echo esc_attr( $ib_seo['title'] ); ?>" />
<?php if ( ! empty( $ib_seo['desc'] ) ) : ?>
<meta property="og:description" content="<?php echo esc_attr( $ib_seo['desc'] ); ?>" />
<?php endif; ?>
<meta property="og:type" content="website" />
<meta property="og:url" content="<?php echo esc_url( ( is_front_page() || is_404() ) ? home_url( '/' ) : get_permalink() ); ?>" />
<meta name="twitter:card" content="summary_large_image" />
<link rel="canonical" href="<?php echo esc_url( ( is_front_page() || is_404() ) ? home_url( '/' ) : get_permalink() ); ?>" />
<?php wp_head(); ?>
</head>
<body <?php body_class(); ?> data-page="<?php echo esc_attr( $ib_key ); ?>" data-lang="en">
<?php wp_body_open(); ?>
<?php get_template_part( 'sprite' ); ?>

<header id="ib-header" class="site-header">
  <div class="wrap nav-inner">
    <a class="brand" href="<?php echo esc_url( home_url( '/' ) ); ?>" aria-label="InkBytes home">
      <svg class="brand-mark" width="24" height="24" viewBox="0 0 1024 1024" aria-hidden="true"><use href="#ink"/></svg>
      <span class="brand-word">InkBytes</span>
      <span class="brand-dot"></span>
    </a>
    <nav class="nav-links" aria-label="Primary">
      <?php
      foreach ( $ib_nav as $n ) :
        $active = in_array( $ib_key, $n['on'], true ) ? ' is-active' : '';
        ?>
        <a href="<?php echo esc_url( ib_url( $n['slug'] ) ); ?>" class="nav-link<?php echo $active; ?>"><?php echo esc_html( $n['label'] ); ?></a>
      <?php endforeach; ?>
      <span class="nav-cta"><a class="ib-btn v-primary sz-sm" href="<?php echo esc_url( inkbytes_reader_url() ); ?>">Start reading</a></span>
    </nav>
  </div>
</header>
