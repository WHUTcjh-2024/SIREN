import { describe, expect, it } from "vitest";
import { getTeacherScope, teacherDemoWorkspace } from "./teacherWorkspace";

describe("getTeacherScope", () => {
  it("keeps metrics, alerts, diagnosis and activity in the same class scope", () => {
    const scope = getTeacherScope(teacherDemoWorkspace, "telecom2402");

    expect(scope.classLabel).toBe("电信科 2402");
    expect(scope.kpis.activeStudents).toBe(40);
    expect(scope.kpis.dataPassRate).toBe(86);
    expect(scope.alerts).toHaveLength(3);
    expect(scope.alerts.every((item) => item.className === "电信科 2402")).toBe(
      true,
    );
    expect(scope.diagnosis.title).toContain("条纹读取");
    expect(scope.activity[2].label).toBe("图像采集");
    expect(scope.activity[2].value).toBeGreaterThan(scope.activity[0].value);
  });

  it("returns the aggregate scope when no class is selected", () => {
    const scope = getTeacherScope(teacherDemoWorkspace, "all");

    expect(scope.kpis).toEqual(teacherDemoWorkspace.kpis);
    expect(scope.alerts).toHaveLength(5);
    expect(scope.diagnosis).toEqual(teacherDemoWorkspace.diagnoses.all);
  });
});
