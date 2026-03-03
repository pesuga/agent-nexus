"use client";
import { useEffect } from "react";

export default function TablerInit() {
  useEffect(() => {
    // Dynamically import Tabler JS on the client side
    // @ts-expect-error Tabler JS has no TS typings; runtime import is intentional.
    void import("@tabler/core/dist/js/tabler.min.js");
  }, []);

  return null;
}
