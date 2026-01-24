import Foundation

struct User: Identifiable, Codable {
    let id: UUID
    let name: String
    let email: String
}
