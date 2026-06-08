/** InkBytes logo mark — exact brand SVG, color-agnostic via `currentColor`.
 *
 * The source file is InkBytes-Logo-White-cropped.svg (viewBox 274 206 481 477).
 * fill="currentColor" lets this render white on the dark header, or any other
 * color by setting the parent's text color.
 *
 * Usage:
 *   <LogoMark className="h-6 w-auto text-white" />
 */

interface LogoMarkProps {
  className?: string;
}

export function LogoMark({ className }: LogoMarkProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="274 206 481 477"
      fill="currentColor"
      fillRule="evenodd"
      className={className}
      aria-hidden="true"
    >
      <path d="M 661 503 L 499 503 L 494 528 L 449 542 L 404 567 L 316 649 L 345 605 L 387 563 L 436 533 L 483 518 L 507 413 L 523 409 L 483 378 L 393 337 L 397 355 L 302 448 L 310 565 L 305 606 L 290 633 L 303 666 L 394 619 L 502 598 L 568 577 L 622 544 Z"/>
      <path d="M 514 423 L 514 493 L 584 493 L 584 424 L 583 423 Z"/>
      <path d="M 596 423 L 596 493 L 664 493 L 664 424 L 663 423 Z"/>
      <path d="M 421 299 L 407 328 L 446 347 L 498 376 L 527 395 L 529 394 L 543 366 L 543 364 L 540 361 L 474 324 L 426 300 Z"/>
      <path d="M 607 351 L 607 411 L 668 411 L 668 351 Z"/>
      <path d="M 681 303 L 681 360 L 738 360 L 738 303 Z"/>
      <path d="M 609 262 L 609 312 L 663 312 L 663 297 L 662 296 L 663 295 L 662 290 L 663 287 L 663 281 L 662 280 L 663 263 L 662 262 Z"/>
      <path d="M 437 396 L 438 398 L 412 452 L 417 463 L 417 473 L 408 485 L 399 488 L 393 487 L 309 652 L 309 646 L 328 602 L 385 485 L 385 481 L 379 472 L 380 461 L 391 450 L 406 449 Z"/>
      <path d="M 544 303 L 544 352 L 596 352 L 596 303 Z"/>
      <path d="M 688 222 L 688 270 L 738 270 L 738 223 L 737 222 Z"/>
      <path d="M 682 395 L 682 401 L 683 402 L 682 403 L 683 406 L 682 410 L 683 412 L 682 438 L 683 439 L 682 441 L 730 441 L 730 395 Z"/>
      <path d="M 554 372 L 554 411 L 595 411 L 596 410 L 595 408 L 596 407 L 595 404 L 595 391 L 596 390 L 595 388 L 595 372 Z"/>
      <path d="M 677 465 L 677 498 L 710 498 L 710 469 L 709 468 L 710 465 Z"/>
    </svg>
  );
}
