<?php
/**
 * Fallback template — used for any non-front-page URL (posts, pages, 404,
 * archives). The marketing landing page lives in front-page.php.
 *
 * @package InkBytes
 */

get_header();
?>

<main id="top">
  <section class="hero" style="padding-bottom:24px">
    <div class="wrap">
      <?php if ( have_posts() ) : ?>
        <h1 class="serif" style="max-width:24ch">
          <?php echo esc_html( is_home() || is_front_page() ? get_bloginfo( 'name' ) : wp_get_document_title() ); ?>
        </h1>
      <?php else : ?>
        <h1 class="serif">Nothing here yet.</h1>
        <p class="sub">That page could not be found. Head back to the <a class="accent" href="<?php echo esc_url( home_url( '/' ) ); ?>">home page</a>.</p>
      <?php endif; ?>
    </div>
  </section>

  <?php if ( have_posts() ) : ?>
  <section style="padding-top:24px">
    <div class="wrap" style="max-width:760px">
      <?php
      while ( have_posts() ) :
        the_post();
        ?>
        <article style="margin-bottom:40px">
          <h2 class="serif" style="text-align:left;max-width:none;margin-bottom:10px">
            <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
          </h2>
          <div class="mock-meta" style="margin-bottom:14px"><span>● <?php echo esc_html( get_the_date() ); ?></span></div>
          <div class="mock-p" style="font-size:16px">
            <?php the_content( esc_html__( 'Continue reading', 'inkbytes' ) ); ?>
          </div>
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
