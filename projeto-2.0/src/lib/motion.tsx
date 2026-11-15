import Lenis from "lenis";
import { motion, useInView, useMotionValue, useSpring, useTransform, type HTMLMotionProps } from "motion/react";
import { useEffect, useRef, type ReactNode } from "react";

export const EASE = [0.22, 1, 0.36, 1] as const;

/** Rolagem com inércia na página pública. Respeita "reduzir movimento". */
export function useSmoothScroll() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const lenis = new Lenis({ duration: 1.15, easing: (t) => 1 - Math.pow(1 - t, 4), wheelMultiplier: 0.9 });
    let frame = requestAnimationFrame(function loop(time) { lenis.raf(time); frame = requestAnimationFrame(loop); });
    const onClick = (event: MouseEvent) => {
      const link = (event.target as HTMLElement).closest<HTMLAnchorElement>('a[href^="#"]');
      if (!link) return;
      const target = document.querySelector<HTMLElement>(link.getAttribute("href")!);
      if (target) { event.preventDefault(); lenis.scrollTo(target, { offset: -70 }); }
    };
    document.addEventListener("click", onClick);
    return () => { cancelAnimationFrame(frame); document.removeEventListener("click", onClick); lenis.destroy(); };
  }, []);
}

/** Cartão que inclina em 3D acompanhando o ponteiro. */
export function Tilt({ children, max = 9, className, ...rest }: { children: ReactNode; max?: number } & HTMLMotionProps<"div">) {
  const ref = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useSpring(useTransform(y, [-0.5, 0.5], [max, -max]), { stiffness: 180, damping: 18 });
  const rotateY = useSpring(useTransform(x, [-0.5, 0.5], [-max, max]), { stiffness: 180, damping: 18 });
  return (
    <motion.div
      ref={ref}
      className={className}
      style={{ rotateX, rotateY, transformPerspective: 900, transformStyle: "preserve-3d" }}
      onPointerMove={(event) => {
        const box = ref.current!.getBoundingClientRect();
        x.set((event.clientX - box.left) / box.width - 0.5);
        y.set((event.clientY - box.top) / box.height - 0.5);
      }}
      onPointerLeave={() => { x.set(0); y.set(0); }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

/** Entra subindo quando aparece na tela. */
export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 28 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-12% 0px" }}
      transition={{ duration: 0.9, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

/** Título que revela linha por linha, de baixo para cima.
    Observa o bloco inteiro (as linhas começam escondidas dentro do recorte). */
export function Lines({ lines, className, delay = 0 }: { lines: ReactNode[]; className?: string; delay?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const visible = useInView(ref, { once: true, margin: "0px 0px -8% 0px" });
  return (
    <span className={className} ref={ref} style={{ display: "block" }}>
      {lines.map((line, index) => (
        <span key={index} style={{ display: "block", overflow: "hidden", paddingBottom: "0.08em" }}>
          <motion.span
            style={{ display: "block" }}
            initial={{ y: "105%" }}
            animate={visible ? { y: 0 } : { y: "105%" }}
            transition={{ duration: 1, delay: delay + index * 0.09, ease: EASE }}
          >
            {line}
          </motion.span>
        </span>
      ))}
    </span>
  );
}
