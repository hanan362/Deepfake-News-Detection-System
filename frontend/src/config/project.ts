/**
 * Project details shown on the About page.
 * Names, roll numbers, supervisor, institution and department were supplied by the team (an empty value is not shown).
 * Nothing is invented here.
 */
export interface TeamMember {
  name: string;
  role: string;
  registration?: string;
}

export const PROJECT = {
  title: "Deepfake News Detection System",
  kind: "Final year project",
  institution: "Muhammad Nawaz Sharif University of Engineering and Technology, Multan",
  department: "Computer Science",
  supervisor: "Mr. Talha Jahangir",
  members: [
    { name: "Mudassar Hussain", role: "Group leader", registration: "Roll no: 2023-CS-163" },
    { name: "Abdul Hannan Anwar", role: "Team member", registration: "Roll no: 2023-CS-25" },
    { name: "Saqlain Muratza", role: "Team member", registration: "Roll no: 2023-CS-79" },
    { name: "Muhammad Ubaid UR Rehman", role: "Team member", registration: "Roll no: 2023-CS-69" },
  ] as TeamMember[],
  repository: "",
};
