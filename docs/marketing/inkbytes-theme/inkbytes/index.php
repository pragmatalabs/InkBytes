<?php
/**
 * Fallback template — search results, archives, and any route not covered by a
 * dedicated template. Marketing pages live in front-page.php / page-*.php.
 *
 * @package InkBytes
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
get_header();
?>
<main>
  <section class="page-hero page-hero--accent">
    <div class="wrap">
      <span class="kicker"><span class="pulse"></span> InkBytes</span>
      <?php if ( have_posts() ) : ?>
        <h1><?php echo esc_html( wp_get_document_title() ); ?></h1>
      <?php else : ?>
        <h1>Nothing here <span class="accent">yet</span>.</h1>
        <p class="lead">That page could not be found. Head back to the <a class="accent" href="<?php echo esc_url( home_url( '/' ) ); ?>">home page</a> or open the <a class="accent" href="<?php echo esc_url( inkbytes_reader_url() ); ?>">reader</a>.</p>
      <?php endif; ?>
    </div>
  </section>

  <?php if ( have_posts() ) : ?>
  <section class="section--tight">
    <div class="article">
      <?php
      while ( have_posts() ) :
        the_post();
        ?>
        <article style="margin-bottom:36px">
          <p class="post-kick"><?php echo esc_html( get_the_date() ); ?></p>
          <h2 class="serif" style="font-size:26px;margin:8px 0 10px"><a href="<?php the_permalink(); ?>"><?php the_title(); ?></a></h2>
          <div class="prose" style="font-size:16px"><?php the_excerpt(); ?></div>
        </article>
        <?php
      endwhile;
      the_posts_pagination();
      ?>
    </div>
  </section>
  <?php endif; ?>
</main>
<?php
get_footer();
