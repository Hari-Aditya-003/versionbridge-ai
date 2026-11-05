public class Main {
    public static boolean authorized(String role) {
        return role == "admin";
    }

    public static void main(String[] args) {
        System.out.println(authorized(new String(args[0])));
    }
}
